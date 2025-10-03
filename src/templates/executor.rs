use anyhow::{Context, Result};
use std::path::Path;
use std::process::Stdio;
use std::time::Duration;
use tokio::process::Command;
use tokio::time::timeout;
use super::models::Template;

pub struct TemplateExecutor;

impl TemplateExecutor {
    pub fn new() -> Self {
        Self
    }
    
    pub async fn execute(&self, template: &Template, output_dir: &Path) -> Result<()> {
        tracing::info!("Executing template: {}", template.name);
        
        // Create output directory for this template
        let template_output_dir = output_dir.join(&template.name);
        tokio::fs::create_dir_all(&template_output_dir)
            .await
            .context("Failed to create template output directory")?;
        
        // Build command
        let mut cmd = Command::new(&template.command.binary);
        cmd.args(&template.command.args);
        
        // Set environment variables
        for (key, value) in &template.env {
            cmd.env(key, value);
        }
        
        // Set working directory
        cmd.current_dir(output_dir);
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());
        
        tracing::debug!(
            "Running command: {} {}",
            template.command.binary,
            template.command.args.join(" ")
        );
        
        // Execute with timeout
        let child = cmd.spawn().context("Failed to spawn command")?;
        
        let result = timeout(Duration::from_secs(template.timeout), child.wait_with_output()).await;
        
        match result {
            Ok(Ok(output)) => {
                if output.status.success() {
                    tracing::info!("✓ Template '{}' completed successfully", template.name);
                    
                    // Log stdout if verbose
                    if !output.stdout.is_empty() {
                        tracing::debug!("stdout: {}", String::from_utf8_lossy(&output.stdout));
                    }
                    
                    Ok(())
                } else {
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    tracing::error!("✗ Template '{}' failed: {}", template.name, stderr);
                    anyhow::bail!("Command failed with status: {}", output.status)
                }
            }
            Ok(Err(e)) => {
                tracing::error!("✗ Template '{}' failed: {}", template.name, e);
                Err(e).context("Failed to wait for command")
            }
            Err(_) => {
                tracing::error!("✗ Template '{}' timed out after {}s", template.name, template.timeout);
                anyhow::bail!("Command timed out after {} seconds", template.timeout)
            }
        }
    }
    
    pub fn resolve_dependencies(&self, templates: &[Template]) -> Result<Vec<Template>> {
        let mut resolved = Vec::new();
        let mut remaining: Vec<_> = templates.to_vec();
        
        while !remaining.is_empty() {
            let initial_len = remaining.len();
            
            remaining.retain(|template| {
                let deps_satisfied = template.depends_on.iter().all(|dep| {
                    resolved.iter().any(|t: &Template| &t.name == dep)
                });
                
                if deps_satisfied {
                    resolved.push(template.clone());
                    false
                } else {
                    true
                }
            });
            
            if remaining.len() == initial_len {
                let unsatisfied: Vec<_> = remaining
                    .iter()
                    .map(|t| format!("{} (depends on: {})", t.name, t.depends_on.join(", ")))
                    .collect();
                
                anyhow::bail!(
                    "Circular dependency or missing templates detected: {}",
                    unsatisfied.join("; ")
                );
            }
        }
        
        Ok(resolved)
    }
}
