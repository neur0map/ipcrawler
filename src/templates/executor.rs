use super::models::Template;
use anyhow::{Context, Result};
use std::collections::{HashMap, HashSet};
use std::io::{self, Write};
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
}

impl TemplateExecutor {
    pub fn new(target: String, output_dir: String, verbose: bool) -> Self {
        Self { target, output_dir, verbose }
    }

    pub async fn execute(&self, template: &Template) -> Result<ExecutionResult> {
        info!("Executing template: {}", template.name);

        let tool_output_dir = format!("{}/raw/{}", self.output_dir, template.name);
        fs::create_dir_all(&tool_output_dir)
            .await
            .context("Failed to create tool output directory")?;

        let args = template.interpolate_args(&self.target, &tool_output_dir);
        
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
                    warn!(
                        "Tool '{}' not found. Please ensure it's installed and in PATH.",
                        template.command.binary
                    );
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
                warn!("Command timed out after {} seconds", template.get_timeout());
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
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        let success = output.status.success();

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
            info!(
                "Template '{}' completed successfully in {:.2}s",
                template.name,
                duration.as_secs_f64()
            );
        } else {
            error!(
                "Template '{}' failed with exit code: {:?}",
                template.name,
                output.status.code()
            );
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

        // Check if any template has dependencies
        let has_dependencies = templates.iter().any(|t| {
            t.depends_on.as_ref().map(|d| !d.is_empty()).unwrap_or(false)
        });

        if has_dependencies {
            info!("Executing templates with dependency resolution");
            self.execute_with_dependencies(templates).await
        } else {
            info!("Executing {} templates in parallel", templates.len());
            self.execute_parallel(templates).await
        }
    }



    async fn execute_parallel(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        use tokio::task::JoinSet;
        use colored::Colorize;

        // Print all tools that will run (non-verbose mode only)
        if !self.verbose {
            for template in &templates {
                println!("  [ ] {}", template.name.dimmed());
            }
            io::stdout().flush().ok();
        }

        let tool_index: Arc<Mutex<HashMap<String, usize>>> = Arc::new(Mutex::new(
            templates.iter().enumerate().map(|(i, t)| (t.name.clone(), i)).collect()
        ));
        
        let mut set: JoinSet<(ExecutionResult, std::time::Duration)> = JoinSet::new();
        
        for template in templates {
            let executor = TemplateExecutor {
                target: self.target.clone(),
                output_dir: self.output_dir.clone(),
                verbose: self.verbose,
            };
            let index_map = tool_index.clone();
            let name = template.name.clone();

            set.spawn(async move {
                let start = std::time::Instant::now();
                let result = match executor.execute(&template).await {
                    Ok(result) => result,
                    Err(e) => {
                        error!("Failed to execute template '{}': {}", template.name, e);
                        ExecutionResult {
                            template_name: template.name.clone(),
                            success: false,
                            duration: Duration::from_secs(0),
                            stdout: String::new(),
                            stderr: e.to_string(),
                            output_file: None,
                        }
                    }
                };

                // Update the line for this tool
                if !executor.verbose {
                    let index_guard = index_map.lock().await;
                    if let Some(&line_num) = index_guard.get(&name) {
                        // Move cursor up to the tool's line, clear it, and rewrite
                        let lines_up = index_guard.len() - line_num;
                        print!("\x1B[{}A", lines_up); // Move cursor up
                        print!("\r\x1B[K"); // Clear line
                        if result.success {
                            println!("  [✓] {} ({:.2}s)", name.green(), start.elapsed().as_secs_f64());
                        } else {
                            println!("  [X] {} (failed)", name.red());
                        }
                        print!("\x1B[{}B", lines_up - 1); // Move cursor back down
                        io::stdout().flush().ok();
                    }
                }
                
                (result, start.elapsed())
            });
        }

        let mut results = Vec::new();
        while let Some(result) = set.join_next().await {
            match result {
                Ok((exec_result, _elapsed)) => {
                    results.push(exec_result);
                }
                Err(e) => error!("Task join error: {}", e),
            }
        }

        // Move cursor past all the tool lines
        if !self.verbose {
            println!();
        }

        results
    }

    async fn execute_with_dependencies(&self, templates: Vec<Template>) -> Vec<ExecutionResult> {
        // Build dependency graph
        let template_map: HashMap<String, Template> = templates
            .into_iter()
            .map(|t| (t.name.clone(), t))
            .collect();

        // Track completed templates
        let completed: Arc<Mutex<HashMap<String, ExecutionResult>>> = 
            Arc::new(Mutex::new(HashMap::new()));
        let failed: Arc<Mutex<HashSet<String>>> = Arc::new(Mutex::new(HashSet::new()));

        // Execute templates respecting dependencies
        self.execute_dag(template_map, completed.clone(), failed.clone()).await;

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
                    error!("Dependency cycle or missing dependencies detected for: {:?}", 
                        pending_guard.iter().collect::<Vec<_>>());
                    
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
                                    println!("  {} {} ({:.2}s)", "✓".green().bold(), name, exec_result.duration.as_secs_f64());
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
                format!("Command failed with no error output")
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
            format!("{}\n... ({} more lines)", preview.join("\n"), lines.len() - max_lines)
        }
    }
}
