use super::models::Template;
use anyhow::{Context, Result};
use std::collections::{HashMap, HashSet};
use std::io::Write;
use std::process::Stdio;
use std::sync::Arc;
use tokio::fs;
use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use tokio::sync::Mutex;
use tokio::time::{timeout, Duration};
use tracing::{debug, error, info, warn};

pub struct TemplateExecutor {
    target: String,
    output_dir: String,
    verbose: bool,
    port_spec: Option<String>,
    wordlist: Option<String>,
}

impl TemplateExecutor {
    pub fn new(
        target: String,
        output_dir: String,
        verbose: bool,
        port_spec: Option<String>,
        wordlist: Option<String>,
    ) -> Self {
        Self {
            target,
            output_dir,
            verbose,
            port_spec,
            wordlist,
        }
    }

    pub async fn execute(&self, template: &Template) -> Result<ExecutionResult> {
        info!("Executing template: {}", template.name);

        let tool_output_dir = format!("{}/raw/{}", self.output_dir, template.name);
        fs::create_dir_all(&tool_output_dir)
            .await
            .context("Failed to create tool output directory")?;

        let args = template.interpolate_args(
            &self.target,
            &tool_output_dir,
            self.port_spec.as_deref(),
            self.wordlist.as_deref(),
        );

        debug!(
            "Running command: {} {}",
            template.command.binary,
            args.join(" ")
        );

        let mut cmd = Command::new(&template.command.binary);
        cmd.args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        if let Some(env_vars) = &template.env {
            for (key, value) in env_vars {
                cmd.env(key, value);
            }
        }

        let start_time = std::time::Instant::now();
        let timeout_duration = Duration::from_secs(template.get_timeout());

        let output = match timeout(timeout_duration, cmd.output()).await {
            Ok(Ok(output)) => output,
            Ok(Err(e)) => {
                if e.kind() == std::io::ErrorKind::NotFound {
                    if self.verbose {
                        warn!(
                            "Tool '{}' not found. Please ensure it's installed and in PATH.",
                            template.command.binary
                        );
                    }
                    return Ok(ExecutionResult {
                        template_name: template.name.clone(),
                        success: false,
                        duration: start_time.elapsed(),
                        stdout: String::new(),
                        stderr: format!("Tool not found: {}", template.command.binary),
                        output_file: None,
                    });
                }
                return Err(e).context("Failed to execute command");
            }
            Err(_) => {
                if self.verbose {
                    warn!("Command timed out after {} seconds", template.get_timeout());
                }
                return Ok(ExecutionResult {
                    template_name: template.name.clone(),
                    success: false,
                    duration: start_time.elapsed(),
                    stdout: String::new(),
                    stderr: format!("Command timed out after {} seconds", template.get_timeout()),
                    output_file: None,
                });
            }
        };

        let duration = start_time.elapsed();
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let mut stderr = String::from_utf8_lossy(&output.stderr).to_string();
        let mut success = output.status.success();

        // Detect silent failures: tools that exit with 0 but produce no meaningful output
        // and complete suspiciously quickly
        if success {
            let is_quick_tool = matches!(
                template.name.as_str(),
                "ping" | "hostname-discovery" | "reverse-dns" | "traceroute"
            );

            // For most tools, < 0.5s execution with minimal output is suspicious
            // Quick tools (ping, dns lookups) are allowed to be fast
            if !is_quick_tool
                && duration.as_millis() < 500
                && stdout.trim().len() < 10
            {
                success = false;
                stderr = format!(
                    "Tool completed too quickly ({:.3}s) with minimal output. Possible causes: missing dependencies, invalid arguments, or target not responding on expected ports/services.",
                    duration.as_secs_f64()
                );
                if self.verbose {
                    warn!(
                        "Tool '{}' completed too quickly ({:.3}s) with minimal output - marking as failed",
                        template.name,
                        duration.as_secs_f64()
                    );
                }
            }
        }

        let output_file = format!("{}/{}_output.txt", tool_output_dir, template.name);
        let mut file = fs::File::create(&output_file)
            .await
            .context("Failed to create output file")?;

        file.write_all(stdout.as_bytes()).await?;
        if !stderr.is_empty() {
            file.write_all(b"\n=== STDERR ===\n").await?;
            file.write_all(stderr.as_bytes()).await?;
        }

        if success {
            if self.verbose {
                info!(
                    "Template '{}' completed successfully in {:.2}s",
                    template.name,
                    duration.as_secs_f64()
                );
            }
        } else {
            if self.verbose {
                error!(
                    "Template '{}' failed with exit code: {:?}",
                    template.name,
                    output.status.code()
                );
            }
        }

        Ok(ExecutionResult {
            template_name: template.name.clone(),
            success,
            duration,
            stdout,
            stderr,
            output_file: Some(output_file),
        })
    }

    pub async fn execute_all(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        
        
        if templates.is_empty() {
            return Vec::new();
        }

        // Detect if we're in a TTY
        let is_tty = atty::is(atty::Stream::Stdout);
        
        if is_tty && !self.verbose {
            // Use indicatif for interactive terminal  
            self.execute_all_with_tui(templates).await
        } else {
            // Use simple output for piped/verbose mode
            self.execute_all_simple(templates).await
        }
    }

    async fn execute_all_with_tui(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
        
        let multi = MultiProgress::new();
        let progress_bars: Arc<Mutex<HashMap<String, ProgressBar>>> = 
            Arc::new(Mutex::new(HashMap::new()));

        let style = ProgressStyle::default_spinner()
            .template("{prefix:>12} {msg}")
            .unwrap();
        
        for template in &templates {
            let pb = multi.add(ProgressBar::new_spinner());
            pb.set_style(style.clone());
            pb.set_prefix("[ ]");
            pb.set_message(template.name.clone());
            pb.enable_steady_tick(std::time::Duration::from_millis(100));
            progress_bars.lock().await.insert(template.name.clone(), pb);
        }

        let (pre_scan_templates, main_templates): (Vec<_>, Vec<_>) =
            templates.into_iter().partition(|t| t.pre_scan);

        let mut all_results = Vec::new();

        if !pre_scan_templates.is_empty() {
            let pre_scan_results = self
                .execute_phase_with_progress(pre_scan_templates, progress_bars.clone())
                .await;
            let hostnames = self.extract_hostnames(&pre_scan_results).await;
            if !hostnames.is_empty() {
                if let Err(_e) = crate::hostname::HostsFileManager::add_entries(&self.target, &hostnames) {}
            }
            all_results.extend(pre_scan_results);
        }

        if !main_templates.is_empty() {
            all_results.extend(
                self.execute_phase_with_progress(main_templates, progress_bars).await
            );
        }

        all_results
    }

    async fn execute_all_simple(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        use colored::Colorize;
        
        if templates.is_empty() {
            return Vec::new();
        }

        if !self.verbose {
            for template in &templates {
                println!("  [ ] {}", template.name.dimmed());
            }
        }

        let (pre_scan_templates, main_templates): (Vec<_>, Vec<_>) =
            templates.into_iter().partition(|t| t.pre_scan);

        let mut all_results = Vec::new();

        if !pre_scan_templates.is_empty() {
            let pre_scan_results = self.execute_phase_simple(pre_scan_templates).await;
            let hostnames = self.extract_hostnames(&pre_scan_results).await;
            if !hostnames.is_empty() {
                if let Err(_e) = crate::hostname::HostsFileManager::add_entries(&self.target, &hostnames) {}
            }
            all_results.extend(pre_scan_results);
        }

        if !main_templates.is_empty() {
            all_results.extend(self.execute_phase_simple(main_templates).await);
        }
        
        if !self.verbose {
            println!();
        }

        all_results
    }

    async fn execute_phase_with_progress(
        &self,
        templates: Vec<Template>,
        progress_bars: Arc<Mutex<HashMap<String, indicatif::ProgressBar>>>,
    ) -> Vec<ExecutionResult> {
        let has_dependencies = templates.iter().any(|t| {
            t.depends_on.as_ref().map(|d| !d.is_empty()).unwrap_or(false)
        });

        if has_dependencies {
            self.execute_with_dependencies(templates).await
        } else {
            self.execute_parallel_with_progress(templates, progress_bars).await
        }
    }

    async fn execute_phase_simple(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        let has_dependencies = templates.iter().any(|t| {
            t.depends_on.as_ref().map(|d| !d.is_empty()).unwrap_or(false)
        });

        if has_dependencies {
            self.execute_with_dependencies(templates).await
        } else {
            self.execute_parallel_simple(templates).await
        }
    }

    async fn execute_parallel_with_progress(
        &self,
        templates: Vec<Template>,
        progress_bars: Arc<Mutex<HashMap<String, indicatif::ProgressBar>>>,
    ) -> Vec<ExecutionResult> {
        use tokio::task::JoinSet;

        let mut set: JoinSet<ExecutionResult> = JoinSet::new();

        for template in templates {
            let executor = TemplateExecutor {
                target: self.target.clone(),
                output_dir: self.output_dir.clone(),
                verbose: self.verbose,
                port_spec: self.port_spec.clone(),
                wordlist: self.wordlist.clone(),
            };
            let name = template.name.clone();
            let pbs = progress_bars.clone();

            set.spawn(async move {
                let start = std::time::Instant::now();
                let result = executor.execute(&template).await.unwrap_or_else(|_e| {
                    ExecutionResult {
                        template_name: template.name.clone(),
                        success: false,
                        duration: Duration::from_secs(0),
                        stdout: String::new(),
                        stderr: "Execution error".to_string(),
                        output_file: None,
                    }
                });

                if let Some(pb) = pbs.lock().await.get(&name) {
                    let elapsed = start.elapsed().as_secs_f64();
                    if result.success {
                        pb.set_prefix("[+]");
                        pb.set_message(format!("{} ({:.2}s)", name, elapsed));
                    } else {
                        pb.set_prefix("[X]");
                        pb.set_message(format!("{} (failed)", name));
                    }
                    pb.finish();
                }

                result
            });
        }

        let mut results = Vec::new();
        while let Some(result) = set.join_next().await {
            if let Ok(exec_result) = result {
                results.push(exec_result);
            }
        }

        results
    }

    async fn execute_parallel_simple(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        use colored::Colorize;
        use tokio::task::JoinSet;

        let mut set: JoinSet<ExecutionResult> = JoinSet::new();

        for template in templates {
            let executor = TemplateExecutor {
                target: self.target.clone(),
                output_dir: self.output_dir.clone(),
                verbose: self.verbose,
                port_spec: self.port_spec.clone(),
                wordlist: self.wordlist.clone(),
            };
            let verbose = executor.verbose;
            let name = template.name.clone();

            set.spawn(async move {
                let start = std::time::Instant::now();
                let result = executor.execute(&template).await.unwrap_or_else(|_e| {
                    ExecutionResult {
                        template_name: template.name.clone(),
                        success: false,
                        duration: Duration::from_secs(0),
                        stdout: String::new(),
                        stderr: "Execution error".to_string(),
                        output_file: None,
                    }
                });

                if !verbose {
                    if result.success {
                        eprintln!("  [+] {} ({:.2}s)", name.green(), start.elapsed().as_secs_f64());
                    } else {
                        eprintln!("  [X] {} (failed)", name.red());
                    }
                }

                result
            });
        }

        let mut results = Vec::new();
        while let Some(result) = set.join_next().await {
            if let Ok(exec_result) = result {
                results.push(exec_result);
            }
        }

        results
    }

        async fn extract_hostnames(&self, results: &[ExecutionResult]) -> Vec<String> {
        use crate::hostname::HostnameExtractor;
        use std::collections::HashSet;

        let mut all_hostnames = HashSet::new();

        for result in results {
            let combined_output = format!("{}\n{}", result.stdout, result.stderr);

            // Extract hostnames based on tool name
            let hostnames = if result.template_name.contains("nmap")
                || result.template_name.contains("hostname")
            {
                HostnameExtractor::from_nmap(&combined_output)
            } else if result.template_name.contains("dns")
                || result.template_name.contains("host")
                || result.template_name.contains("reverse")
                || result.template_name.contains("dig")
            {
                HostnameExtractor::from_reverse_dns(&combined_output)
            } else {
                // Try both extractors for unknown tools
                let mut h = HostnameExtractor::from_nmap(&combined_output);
                h.extend(HostnameExtractor::from_reverse_dns(&combined_output));
                h
            };

            for hostname in hostnames {
                debug!(
                    "Extracted hostname '{}' from template '{}'",
                    hostname, result.template_name
                );
                all_hostnames.insert(hostname);
            }
        }

        all_hostnames.into_iter().collect()
    }

    async fn execute_with_dependencies(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        // Build dependency graph
        let template_map: HashMap<String, Template> =
            templates.into_iter().map(|t| (t.name.clone(), t)).collect();

        // Track completed templates
        let completed: Arc<Mutex<HashMap<String, ExecutionResult>>> =
            Arc::new(Mutex::new(HashMap::new()));
        let failed: Arc<Mutex<HashSet<String>>> = Arc::new(Mutex::new(HashSet::new()));

        // Execute templates respecting dependencies
        self.execute_dag(template_map, completed.clone(), failed.clone())
            .await;

        // Return results in order
        let completed_guard = completed.lock().await;
        let results: Vec<ExecutionResult> = completed_guard.values().cloned().collect();
        results
    }

    async fn execute_dag(
        &self,
        template_map: HashMap<String, Template>,
        completed: Arc<Mutex<HashMap<String, ExecutionResult>>>,
        failed: Arc<Mutex<HashSet<String>>>,
    ) {
        use tokio::task::JoinSet;

        let template_map = Arc::new(template_map);
        let mut set: JoinSet<(String, ExecutionResult)> = JoinSet::new();
        let pending: Arc<Mutex<HashSet<String>>> =
            Arc::new(Mutex::new(template_map.keys().cloned().collect()));

        loop {
            // Find templates ready to execute (no pending dependencies)
            let ready_templates = {
                let pending_guard = pending.lock().await;
                let completed_guard = completed.lock().await;
                let failed_guard = failed.lock().await;

                pending_guard
                    .iter()
                    .filter_map(|name| {
                        let template = template_map.get(name)?;

                        // Check if dependencies are satisfied
                        if let Some(deps) = &template.depends_on {
                            // Check if any dependency failed
                            if deps.iter().any(|dep| failed_guard.contains(dep)) {
                                return None; // Skip if dependency failed
                            }

                            // Check if all dependencies completed
                            if deps.iter().all(|dep| completed_guard.contains_key(dep)) {
                                Some(template.clone())
                            } else {
                                None // Wait for dependencies
                            }
                        } else {
                            // No dependencies, ready to run
                            Some(template.clone())
                        }
                    })
                    .collect::<Vec<_>>()
            };

            if ready_templates.is_empty() {
                // Check if we're done or stuck
                let pending_guard = pending.lock().await;
                if pending_guard.is_empty() {
                    break; // All done
                }

                // Check if we have any running tasks
                if set.is_empty() {
                    // No ready templates and nothing running = dependency cycle or missing deps
                    error!(
                        "Dependency cycle or missing dependencies detected for: {:?}",
                        pending_guard.iter().collect::<Vec<_>>()
                    );

                    // Mark remaining as failed
                    let mut failed_guard = failed.lock().await;
                    for name in pending_guard.iter() {
                        failed_guard.insert(name.clone());
                    }
                    break;
                }

                // Wait for at least one task to complete
                if let Some(result) = set.join_next().await {
                    match result {
                        Ok((name, exec_result)) => {
                            // Print completion indicator in non-verbose mode
                            if !self.verbose {
                                use colored::Colorize;
                                if exec_result.success {
                                    println!(
                                        "  {} {} ({:.2}s)",
                                        "✓".green().bold(),
                                        name,
                                        exec_result.duration.as_secs_f64()
                                    );
                                } else {
                                    println!("  {} {} (failed)", "✗".red().bold(), name);
                                }
                                let _ = std::io::stdout().flush();
                            }

                            let mut pending_guard = pending.lock().await;
                            pending_guard.remove(&name);

                            if exec_result.success {
                                let mut completed_guard = completed.lock().await;
                                completed_guard.insert(name, exec_result);
                            } else {
                                let mut failed_guard = failed.lock().await;
                                failed_guard.insert(name);
                            }
                        }
                        Err(e) => error!("Task join error: {}", e),
                    }
                }
                continue;
            }

            // Spawn tasks for ready templates
            for template in ready_templates {
                let name = template.name.clone();
                let executor = TemplateExecutor {
                    target: self.target.clone(),
                    output_dir: self.output_dir.clone(),
                    verbose: self.verbose,
                    port_spec: self.port_spec.clone(),
                    wordlist: self.wordlist.clone(),
                };

                set.spawn(async move {
                    info!("Executing template: {}", name);
                    let result = match executor.execute(&template).await {
                        Ok(result) => result,
                        Err(e) => {
                            error!("Failed to execute template '{}': {}", name, e);
                            ExecutionResult {
                                template_name: name.clone(),
                                success: false,
                                duration: Duration::from_secs(0),
                                stdout: String::new(),
                                stderr: e.to_string(),
                                output_file: None,
                            }
                        }
                    };
                    (name, result)
                });
            }

            // Wait for at least one task to complete before checking for new ready tasks
            if let Some(result) = set.join_next().await {
                match result {
                    Ok((name, exec_result)) => {
                        let mut pending_guard = pending.lock().await;
                        pending_guard.remove(&name);

                        if exec_result.success {
                            let mut completed_guard = completed.lock().await;
                            completed_guard.insert(name, exec_result);
                        } else {
                            let mut failed_guard = failed.lock().await;
                            failed_guard.insert(name);
                        }
                    }
                    Err(e) => error!("Task join error: {}", e),
                }
            }
        }

        // Wait for remaining tasks to complete
        while let Some(result) = set.join_next().await {
            match result {
                Ok((name, exec_result)) => {
                    if exec_result.success {
                        let mut completed_guard = completed.lock().await;
                        completed_guard.insert(name, exec_result);
                    } else {
                        let mut failed_guard = failed.lock().await;
                        failed_guard.insert(name);
                    }
                }
                Err(e) => error!("Task join error: {}", e),
            }
        }
    }
}

#[derive(Debug, Clone)]
pub struct ExecutionResult {
    pub template_name: String,
    pub success: bool,
    pub duration: Duration,
    pub stdout: String,
    pub stderr: String,
    pub output_file: Option<String>,
}

impl ExecutionResult {
    pub fn get_error_details(&self) -> Option<String> {
        if !self.success {
            Some(if !self.stderr.is_empty() {
                self.stderr.clone()
            } else {
                "Command failed with no error output".to_string()
            })
        } else {
            None
        }
    }

    pub fn get_output_preview(&self, max_lines: usize) -> String {
        let lines: Vec<&str> = self.stdout.lines().collect();
        if lines.len() <= max_lines {
            self.stdout.clone()
        } else {
            let preview: Vec<&str> = lines.iter().take(max_lines).copied().collect();
            format!(
                "{}\n... ({} more lines)",
                preview.join("\n"),
                lines.len() - max_lines
            )
        }
    }
}
