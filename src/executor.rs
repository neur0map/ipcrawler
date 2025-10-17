use anyhow::{Context, Result};
use colored::*;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::process::Stdio;
use std::sync::Arc;
use tokio::process::Command;
use tokio::sync::Semaphore;
use uuid::Uuid;

use crate::output::OutputManager;
use crate::template::{TemplateManager, ToolTemplate};
use crate::reporter::ReportGenerator;

pub struct Executor {
    targets: Vec<String>,
    output_dir: String,
    verbose: bool,
    template_manager: TemplateManager,
    output_manager: OutputManager,
    report_generator: ReportGenerator,
    max_concurrent: usize,
}

impl Executor {
    pub fn new(
        targets: Vec<String>,
        output_path: Option<std::path::PathBuf>,
        verbose: bool,
        template_manager: TemplateManager,
    ) -> Result<Self> {
        let output_dir = match output_path {
            Some(path) => path.to_string_lossy().to_string(),
            None => std::env::current_dir()?.to_string_lossy().to_string(),
        };
        
        let output_manager = OutputManager::new(&output_dir)?;
        let report_generator = ReportGenerator::new(&output_dir)?;
        
        Ok(Executor {
            targets,
            output_dir,
            verbose,
            template_manager,
            output_manager,
            report_generator,
            max_concurrent: 10, // Configurable parallel execution
        })
    }
    
    pub async fn execute(&mut self) -> Result<()> {
        println!("{} Starting IPCrawler reconnaissance...", "🔍".blue());
        println!("{} Targets: {}", "→".blue(), self.targets.join(", "));
        println!("{} Output: {}", "→".blue(), self.output_dir);
        println!();
        
        let templates = self.template_manager.get_all_templates();
        let multi_progress = MultiProgress::new();
        let semaphore = Arc::new(Semaphore::new(self.max_concurrent));
        
        let mut handles = vec![];
        
        for template in templates {
            for target in &self.targets {
                let permit = semaphore.clone().acquire_owned().await?;
                let template = template.clone();
                let target = target.clone();
                let output_manager = self.output_manager.clone();
                let verbose = self.verbose;
                let pb = multi_progress.add(ProgressBar::new_spinner());
                
                pb.set_style(
                    ProgressStyle::default_spinner()
                        .template("{spinner:.green} {msg}")
                        .unwrap()
                );
                pb.set_message(format!("{}: {}", template.name, target));
                
                let handle = tokio::spawn(async move {
                    let _permit = permit; // Hold permit for the duration of the task
                    
                    let result = Self::execute_tool(&template, &target, &output_manager, verbose).await;
                    
                    if result.is_ok() {
                        pb.finish_with_message(format!("✓ {}: {}", template.name, target));
                    } else {
                        pb.finish_with_message(format!("✗ {}: {}", template.name, target));
                    }
                    
                    (template, target, result)
                });
                
                handles.push(handle);
            }
        }
        
        // Wait for all tasks to complete
        let results = handles;
        
        // Generate reports
        println!("\n{} Generating reports...", "📝".blue());
        self.report_generator.generate_reports(results).await?;
        
        Ok(())
    }
    
    async fn execute_tool(
        template: &ToolTemplate,
        target: &str,
        output_manager: &OutputManager,
        verbose: bool,
    ) -> Result<()> {
        let output_file = template.output_file
            .as_ref()
            .map(|f| f.replace("{target}", target))
            .unwrap_or_else(|| format!("{}.txt", Uuid::new_v4()));
        
        // Build command with target substitution
        let mut command = Command::new(&template.command);
        for arg in &template.args {
            let substituted_arg = arg.replace("{target}", target);
            command.arg(&substituted_arg);
        }
        
        // Configure output
        let _output_path = output_manager.get_raw_output_path(&output_file);
        command.stdout(Stdio::piped());
        command.stderr(Stdio::piped());
        
        if verbose {
            println!("Executing: {} {}", template.command, template.args.join(" "));
        }
        
        let mut child = command.spawn()
            .with_context(|| format!("Failed to spawn {} command", template.command))?;
        
        let stdout = child.stdout.take().unwrap();
        let stderr = child.stderr.take().unwrap();
        
        // Capture output asynchronously
        let output_handle = tokio::spawn(async move {
            use tokio::io::AsyncReadExt;
            
            let mut output = String::new();
            let mut buf = [0; 1024];
            let mut stdout = stdout;
            
            loop {
                match stdout.read(&mut buf).await {
                    Ok(0) => break,
                    Ok(n) => output.push_str(&String::from_utf8_lossy(&buf[..n])),
                    Err(_) => break,
                }
            }
            
            output
        });
        
        let error_handle = tokio::spawn(async move {
            use tokio::io::AsyncReadExt;
            
            let mut error = String::new();
            let mut buf = [0; 1024];
            let mut stderr = stderr;
            
            loop {
                match stderr.read(&mut buf).await {
                    Ok(0) => break,
                    Ok(n) => error.push_str(&String::from_utf8_lossy(&buf[..n])),
                    Err(_) => break,
                }
            }
            
            error
        });
        
        let status = child.wait().await?;
        let output = output_handle.await?;
        let error = error_handle.await?;
        
        if !status.success() {
            return Err(anyhow::anyhow!(
                "Command failed with status {}: {}",
                status,
                error
            ));
        }
        
        // Save output
        output_manager.save_raw_output(&output_file, &output).await?;
        
        Ok(())
    }
}
