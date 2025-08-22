use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use colored::*;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Config {
    pub metadata: Metadata,
    pub tools: Vec<Tool>,
    pub chains: Vec<Chain>,
    pub globals: Globals,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Metadata {
    pub name: String,
    pub description: String,
    pub version: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Tool {
    pub name: String,
    pub command: String,
    pub timeout: u64,
    pub output_file: String,
    pub enabled: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<std::collections::HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Chain {
    pub name: String,
    pub from: String,
    pub to: String,
    pub condition: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Globals {
    pub max_concurrent: usize,
    pub retry_count: u32,
    pub log_level: String,
}

impl Config {
    pub fn from_file(path: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let contents = fs::read_to_string(path)?;
        let config: Config = serde_yaml::from_str(&contents)?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), Box<dyn std::error::Error>> {
        if self.metadata.name.is_empty() {
            return Err("Config metadata name cannot be empty".into());
        }

        if self.metadata.version.is_empty() {
            return Err("Config metadata version cannot be empty".into());
        }

        if self.tools.is_empty() {
            return Err("Config must contain at least one tool".into());
        }

        // Enhanced validation with tool availability checking
        let checker = crate::doctor::DependencyChecker::new();
        let mut warnings = Vec::new();

        for tool in &self.tools {
            if tool.name.is_empty() {
                return Err("Tool name cannot be empty".into());
            }
            if tool.command.is_empty() {
                return Err(format!("Tool '{}' command cannot be empty", tool.name).into());
            }
            if tool.timeout == 0 {
                return Err(format!("Tool '{}' timeout must be greater than 0", tool.name).into());
            }
            
            // Check tool availability if enabled
            if tool.enabled {
                // Extract base command from tool.command
                let base_cmd = tool.command.split_whitespace()
                    .next()
                    .unwrap_or("");
                
                if checker.find_tool_path(base_cmd).is_none() {
                    if let Some(alternative) = checker.find_alternative_tool(tool) {
                        warnings.push(format!(
                            "⚠️  Tool '{}' not found. Consider using '{}' instead",
                            base_cmd, alternative
                        ));
                    } else {
                        warnings.push(format!(
                            "⚠️  Tool '{}' not found and no alternatives available",
                            base_cmd
                        ));
                    }
                }
            }
        }
        
        // Print warnings but don't fail validation
        for warning in warnings {
            eprintln!("{}", warning.yellow());
        }

        for chain in &self.chains {
            if chain.name.is_empty() {
                return Err("Chain name cannot be empty".into());
            }
            
            let from_exists = self.tools.iter().any(|t| t.name == chain.from);
            let to_exists = self.tools.iter().any(|t| t.name == chain.to);
            
            if !from_exists {
                return Err(format!("Chain '{}' references non-existent tool '{}'", chain.name, chain.from).into());
            }
            if !to_exists {
                return Err(format!("Chain '{}' references non-existent tool '{}'", chain.name, chain.to).into());
            }
            
            let valid_conditions = vec!["has_output", "exit_success", "contains", "file_size"];
            if !valid_conditions.contains(&chain.condition.as_str()) {
                return Err(format!("Chain '{}' has invalid condition '{}'", chain.name, chain.condition).into());
            }
        }

        if self.globals.max_concurrent == 0 {
            return Err("Global max_concurrent must be greater than 0".into());
        }

        let valid_log_levels = vec!["trace", "debug", "info", "warn", "error"];
        if !valid_log_levels.contains(&self.globals.log_level.as_str()) {
            return Err(format!("Invalid log level '{}'", self.globals.log_level).into());
        }

        Ok(())
    }

    pub fn replace_variables(&mut self, target: &str, output: &str) {
        for tool in &mut self.tools {
            tool.command = tool.command.replace("{target}", target);
            tool.command = tool.command.replace("{output}", output);
            tool.output_file = tool.output_file.replace("{target}", target);
            tool.output_file = tool.output_file.replace("{output}", output);
        }
    }

    pub fn print_summary(&self) {
        println!("\n{}", "Configuration Summary:".bright_cyan().bold());
        println!("  {} {}", "Profile:".bright_blue(), self.metadata.name);
        println!("  {} {}", "Version:".bright_blue(), self.metadata.version);
        println!("  {} {}", "Description:".bright_blue(), self.metadata.description);
        
        println!("\n  {}:", "Tools".bright_green());
        for tool in &self.tools {
            let status = if tool.enabled { "[ENABLED]".green() } else { "[DISABLED]".red() };
            println!("    {} {} (timeout: {}s)", status, tool.name, tool.timeout);
        }
        
        if !self.chains.is_empty() {
            println!("\n  {}:", "Chains".bright_yellow());
            for chain in &self.chains {
                println!("    - {} → {} ({})", chain.from, chain.to, chain.condition);
            }
        }
        
        println!("\n  {}:", "Globals".bright_magenta());
        println!("    Max concurrent: {}", self.globals.max_concurrent);
        println!("    Retry count: {}", self.globals.retry_count);
        println!("    Log level: {}", self.globals.log_level);
    }
}