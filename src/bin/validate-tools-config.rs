use regex::Regex;
use serde_yaml;
use std::collections::HashMap;
use std::path::Path;
use std::process;

#[derive(serde::Deserialize)]
struct ToolsConfig {
    tools: HashMap<String, ToolDefinition>,
    generic_patterns: Option<Vec<PatternDefinition>>,
}

#[derive(serde::Deserialize)]
struct ToolDefinition {
    name: String,
    command: String,
    patterns: Option<Vec<PatternDefinition>>,
}

#[derive(serde::Deserialize)]
struct PatternDefinition {
    name: String,
    regex: String,
    #[serde(rename = "type")]
    _pattern_type: String,
    confidence: Option<f64>,
}

fn main() {
    println!("🔍 Validating tools configuration...");
    
    // Validate tools.yaml
    let config_path = Path::new("config/tools.yaml");
    if !config_path.exists() {
        eprintln!("❌ Tools configuration file not found: {}", config_path.display());
        process::exit(1);
    }
    
    // Read and parse YAML
    let content = match std::fs::read_to_string(config_path) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("❌ Failed to read tools config: {}", e);
            process::exit(1);
        }
    };
    
    let config: ToolsConfig = match serde_yaml::from_str(&content) {
        Ok(config) => config,
        Err(e) => {
            eprintln!("❌ Failed to parse YAML: {}", e);
            process::exit(1);
        }
    };
    
    println!("✓ YAML syntax is valid");
    
    // Validate structure
    if config.tools.is_empty() {
        eprintln!("❌ No tools defined in configuration");
        process::exit(1);
    }
    
    println!("✓ Found {} tools in configuration", config.tools.len());
    
    // Validate each tool
    for (tool_name, tool) in &config.tools {
        if tool.name.is_empty() || tool.command.is_empty() {
            eprintln!("❌ Tool '{}' has empty name or command", tool_name);
            process::exit(1);
        }
        
        // Validate patterns if present
        if let Some(patterns) = &tool.patterns {
            for pattern in patterns {
                if let Err(e) = Regex::new(&pattern.regex) {
                    eprintln!("❌ Invalid regex in tool '{}', pattern '{}': {}", 
                        tool_name, pattern.name, e);
                    process::exit(1);
                }
                
                // Validate confidence if present
                if let Some(conf) = pattern.confidence {
                    if conf < 0.0 || conf > 1.0 {
                        eprintln!("❌ Invalid confidence {} in pattern '{}' (must be 0.0-1.0)",
                            conf, pattern.name);
                        process::exit(1);
                    }
                }
            }
        }
    }
    
    // Validate generic patterns
    if let Some(patterns) = &config.generic_patterns {
        for pattern in patterns {
            if let Err(e) = Regex::new(&pattern.regex) {
                eprintln!("❌ Invalid regex in generic pattern '{}': {}", 
                    pattern.name, e);
                process::exit(1);
            }
        }
        println!("✓ Found {} valid generic patterns", patterns.len());
    }
    
    println!("✅ Tools configuration validation passed!");
    println!("📋 Summary:");
    println!("  • Tools: {}", config.tools.len());
    if let Some(patterns) = &config.generic_patterns {
        println!("  • Generic patterns: {}", patterns.len());
    }
    
    let total_patterns: usize = config.tools.values()
        .filter_map(|t| t.patterns.as_ref())
        .map(|p| p.len())
        .sum();
    println!("  • Tool-specific patterns: {}", total_patterns);
}