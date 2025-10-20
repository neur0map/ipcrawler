use anyhow::{Context, Result};
use colored::*;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;
use tokio::process::Command;
use tokio::sync::Semaphore;
use futures::future::join_all;

use crate::core::detector::SystemDetector;
use crate::core::parser::LLMParser;
use crate::template::manager::{TemplateManager, ToolTemplate};
use crate::providers::ParsedResult;
use crate::report::generator::ReportGenerator;

pub struct Executor {
    targets: Vec<String>,
    #[allow(dead_code)]
    output_dir: String,
    verbose: bool,
    port_range: Option<String>,
    system_detector: SystemDetector,
    template_manager: TemplateManager,
    llm_parser: LLMParser,
    report_generator: ReportGenerator,
    max_concurrent: usize,
    results: Vec<ParsedResult>,
}

impl Executor {
    pub fn new(
        targets: Vec<String>,
        output_path: Option<std::path::PathBuf>,
        verbose: bool,
        port_range: Option<String>,
        system_detector: SystemDetector,
        template_manager: TemplateManager,
        llm_parser: LLMParser,
    ) -> Result<Self> {
        let output_dir = match output_path {
            Some(path) => path.to_string_lossy().to_string(),
            None => std::env::current_dir()?.to_string_lossy().to_string(),
        };
        
        let report_generator = ReportGenerator::new(&output_dir)?;
        
        Ok(Executor {
            targets,
            output_dir,
            verbose,
            port_range,
            system_detector,
            template_manager,
            llm_parser,
            report_generator,
            max_concurrent: 10,
            results: Vec::new(),
        })
    }

    pub async fn execute(&mut self) -> Result<()> {
        if self.verbose {
            println!("{} Starting reconnaissance on {} targets", "Info:".blue(), self.targets.len());
            self.show_system_info();
        }

        // Get applicable templates based on system capabilities
        let templates = self.get_scan_templates()?;
        
        if self.verbose {
            println!("{} Using {} templates", "Info:".blue(), templates.len());
        }

        // Create progress bars
        let multi_progress = MultiProgress::new();
        let main_progress = multi_progress.add(
            ProgressBar::new((self.targets.len() * templates.len()) as u64)
        );
        
        main_progress.set_style(
            ProgressStyle::default_bar()
                .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} {msg:.dim}")
                .unwrap()
                .progress_chars("#>-")
        );

        // Execute tools for all targets
        let semaphore = Arc::new(Semaphore::new(self.max_concurrent));
        let mut tasks = Vec::new();

        for target in &self.targets {
            for template in &templates {
                let target = target.clone();
                let template = template.clone();
                let port_range = self.port_range.clone();
                let verbose = self.verbose;
                let system_detector = self.system_detector.clone();
                let llm_parser = self.llm_parser.clone();
                let semaphore = semaphore.clone();
                let main_progress = main_progress.clone();

                let template_manager_clone = self.template_manager.clone();
                let task = tokio::spawn(async move {
                    let _permit = semaphore.acquire().await.unwrap();
                    
                    main_progress.set_message(format!("Running {} on {}", template.name, target));
                    
                    let result = Executor::execute_tool(&target, &template, port_range.as_deref(), verbose, &system_detector, &llm_parser, &template_manager_clone).await;
                    
                    // Increment progress bar regardless of success/failure
                    main_progress.inc(1);
                    
                    match result {
                        Ok(parsed_result) => {
                            if verbose {
                                println!("✓ {} on {} completed successfully", template.name, target);
                            }
                            Some(parsed_result)
                        }
                        Err(e) => {
                            if verbose {
                                eprintln!("✗ {} on {} failed: {}", template.name, target, e);
                            }
                            None
                        }
                    }
                });
                
                tasks.push(task);
            }
        }

        // Wait for all tasks to complete
        let results = join_all(tasks).await;
        main_progress.finish_with_message("Scan completed");

        // Collect results
        for result in results {
            if let Ok(Some(parsed_result)) = result {
                self.results.push(parsed_result);
            }
        }

        if self.verbose {
            println!("{} {} results collected", "Info:".blue(), self.results.len());
        }

        // Generate reports
        self.generate_reports().await?;

        Ok(())
    }

    async fn execute_tool(
        target: &str,
        template: &ToolTemplate,
        port_range: Option<&str>,
        verbose: bool,
        system_detector: &SystemDetector,
        llm_parser: &LLMParser,
        template_manager: &TemplateManager,
    ) -> Result<ParsedResult> {
        // Check if tool is available
        if !system_detector.is_tool_available(&template.command) {
            return Err(anyhow::anyhow!("Tool {} not available", template.command));
        }

        // Check dependencies
        if let Some(ref deps) = template.dependencies {
            for dep in deps {
                if !system_detector.is_tool_available(dep) {
                    return Err(anyhow::anyhow!("Dependency {} not available", dep));
                }
            }
        }

        // Build command
        let command_str = template_manager.render_command(template, target, port_range)?;

        if verbose {
            println!("Executing: {}", command_str);
        }

        // Execute command (templates are pre-filtered for sudo requirements)
        let output = Executor::run_command(&command_str, template.timeout_seconds, system_detector).await?;
        
        if verbose {
            println!("Command completed, output length: {} bytes", output.len());
        }

        // Parse output with LLM
        let parse_request = crate::providers::ParseRequest {
            tool_name: template.name.clone(),
            raw_output: output.clone(),
            target: target.to_string(),
            max_tokens: None,
        };

        let parsed_result = llm_parser.parse(parse_request).await?;

        // Save raw output
        Executor::save_raw_output(&template.name, target, &output, system_detector, template_manager).await?;

        Ok(parsed_result)
    }

    async fn run_command(command_str: &str, timeout_seconds: Option<u64>, system_detector: &SystemDetector) -> Result<String> {
        let parts: Vec<&str> = command_str.split_whitespace().collect();
        if parts.is_empty() {
            return Err(anyhow::anyhow!("Empty command"));
        }

        let tool_name = parts[0];
        let system_info = system_detector.get_system_info();
        
        // Check if tool requires sudo and prepend if needed
        let mut cmd = if SystemDetector::tool_requires_sudo(tool_name, system_info) {
            let mut sudo_cmd = Command::new("sudo");
            sudo_cmd.arg(tool_name);
            for arg in &parts[1..] {
                sudo_cmd.arg(arg);
            }
            sudo_cmd
        } else {
            let mut cmd = Command::new(tool_name);
            for arg in &parts[1..] {
                cmd.arg(arg);
            }
            cmd
        };

        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let timeout = Duration::from_secs(timeout_seconds.unwrap_or(300)); // 5 minutes default

        let output = tokio::time::timeout(timeout, cmd.output()).await
            .map_err(|_| anyhow::anyhow!("Command timed out after {} seconds", timeout.as_secs()))?
            .context("Failed to execute command")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            let stdout = String::from_utf8_lossy(&output.stdout);
            return Err(anyhow::anyhow!(
                "Command failed with exit code {}: {}\n{}",
                output.status.code().unwrap_or(-1),
                stderr,
                stdout
            ));
        }

        let stdout = String::from_utf8(output.stdout)
            .context("Command output was not valid UTF-8")?;
        
        let stderr = String::from_utf8(output.stderr)
            .context("Command stderr was not valid UTF-8")?;
        
        Ok(stdout + &stderr)
    }

    

    async fn save_raw_output(tool_name: &str, target: &str, output: &str, system_detector: &SystemDetector, template_manager: &TemplateManager) -> Result<()> {
        // Create output directory if it doesn't exist
        let output_dir = format!("ipcrawler_results/{}", target.replace('.', "_"));
        tokio::fs::create_dir_all(&output_dir).await?;

        // Get the template for this tool to use custom output file naming
        let templates = template_manager.get_applicable_templates(system_detector.get_system_info());
        let filename = if let Some(template) = templates.iter().find(|t| t.name == tool_name) {
            // Use template's custom output file pattern if available
            if let Some(custom_filename) = template_manager.render_output_file(template, target)? {
                format!("{}/{}", output_dir, custom_filename)
            } else {
                // Fallback to default naming
                format!("{}/{}_{}.txt", output_dir, tool_name, chrono::Utc::now().format("%Y%m%d_%H%M%S"))
            }
        } else {
            // Fallback to default naming
            format!("{}/{}_{}.txt", output_dir, tool_name, chrono::Utc::now().format("%Y%m%d_%H%M%S"))
        };
        
        tokio::fs::write(&filename, output).await?;

        Ok(())
    }

    fn get_scan_templates(&self) -> Result<Vec<ToolTemplate>> {
        // Get templates that are applicable to the current system
        let applicable_templates = self.template_manager.get_applicable_templates(self.system_detector.get_system_info());
        
        // Filter templates based on available tools
        let available_templates: Vec<ToolTemplate> = applicable_templates
            .into_iter()
            .filter(|template| {
                self.system_detector.is_tool_available(&template.command) &&
                template.dependencies.as_ref().map_or(true, |deps| {
                    deps.iter().all(|dep| self.system_detector.is_tool_available(dep))
                })
            })
            .cloned()
            .collect();

        if available_templates.is_empty() {
            return Err(anyhow::anyhow!(
                "No applicable templates found. Install tools: {}",
                self.system_detector.get_tool_recommendations().join(", ")
            ));
        }

        Ok(available_templates)
    }

    fn show_system_info(&self) {
        let system_info = self.system_detector.get_system_info();
        
        println!("{} System Information:", "System:".cyan());
        println!("  OS: {:?}", system_info.os);
        println!("  Architecture: {}", system_info.arch);
        println!("  Sudo Access: {}", if system_info.has_sudo { "Yes" } else { "No" });
        println!("  Shell: {}", system_info.shell);
        
        let available_tools = self.system_detector.get_available_tools();
        println!("  Available Tools: {}", available_tools.len());
        
        if self.verbose {
            for tool in available_tools {
                println!("    {} {} ({})", 
                    if tool.is_available { "✓" } else { "✗" },
                    tool.name,
                    tool.version.as_ref().unwrap_or(&"unknown".to_string())
                );
            }
        }
        
        let missing_tools = self.system_detector.get_missing_tools();
        if !missing_tools.is_empty() {
            println!("  Missing Tools: {}", missing_tools.len());
            if self.verbose {
                for tool in missing_tools {
                    println!("    ✗ {}", tool);
                }
            }
        }
    }

    async fn generate_reports(&self) -> Result<()> {
        if self.results.is_empty() {
            if self.verbose {
                println!("{} No results to report", "Warning:".yellow());
            }
            return Ok(());
        }

        if self.verbose {
            println!("{} Generating reports...", "Info:".blue());
        }

        // Generate JSON report
        let json_report = self.report_generator.generate_json_report(&self.results)?;
        let json_path = self.report_generator.get_json_report_path();
        tokio::fs::write(&json_path, json_report).await?;

        // Generate Markdown report
        let markdown_report = self.report_generator.generate_markdown_report(&self.results)?;
        let markdown_path = self.report_generator.get_markdown_report_path();
        tokio::fs::write(&markdown_path, markdown_report).await?;
        
        if self.verbose {
            println!("{} Markdown report saved to {}", "✓".green(), markdown_path);
        }

        // Show summary
        self.show_summary();

        Ok(())
    }

    fn show_summary(&self) {
        println!("\n{} Scan Summary:", "Summary:".cyan());
        
        let mut tool_counts = std::collections::HashMap::new();
        let mut total_findings = 0;
        
        for result in &self.results {
            *tool_counts.entry(result.tool_name.clone()).or_insert(0) += 1;
            if let Some(findings) = result.findings["findings"].as_array() {
                total_findings += findings.len();
            }
        }
        
        println!("  Targets Scanned: {}", self.targets.len());
        println!("  Tools Executed: {}", tool_counts.len());
        println!("  Total Results: {}", self.results.len());
        println!("  Total Findings: {}", total_findings);
        
        if !tool_counts.is_empty() {
            println!("  Tools Used:");
            for (tool, count) in tool_counts {
                println!("    {}: {} executions", tool, count);
            }
        }
    }

    
}