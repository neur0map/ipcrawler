use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use tera::{Tera, Context as TeraContext};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolTemplate {
    pub name: String,
    pub description: String,
    pub command: String,
    pub args: Vec<String>,
    pub output_file: Option<String>,
    pub category: String,
    pub dependencies: Option<Vec<String>>,
    pub parse_strategy: String, // "llm" or "regex"
    pub output_format: String,  // "json" or "raw"
    pub requires_sudo: Option<bool>,
    pub timeout_seconds: Option<u64>,
    pub max_retries: Option<u32>,
    pub conditions: Option<TemplateConditions>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateConditions {
    pub os: Option<Vec<String>>,           // ["linux", "windows", "macos"]
    pub tools_present: Option<Vec<String>>, // ["nmap", "dig"]
    pub tools_absent: Option<Vec<String>>,  // ["masscan"]
    pub has_sudo: Option<bool>,
}

#[derive(Debug, Deserialize)]
pub struct TemplateConfig {
    pub tools: HashMap<String, ToolTemplate>,
}

pub struct TemplateManager {
    templates: HashMap<String, ToolTemplate>,
    templates_dir: String,
    tera: Tera,
}

impl TemplateManager {
    pub fn new(templates_dir: &str) -> Result<Self> {
        let mut manager = TemplateManager {
            templates: HashMap::new(),
            templates_dir: templates_dir.to_string(),
            tera: Tera::default(),
        };
        
        manager.load_templates()?;
        Ok(manager)
    }

    fn load_templates(&mut self) -> Result<()> {
        let templates_path = Path::new(&self.templates_dir);
        
        if !templates_path.exists() {
            return Err(anyhow::anyhow!("Templates directory not found: {}", self.templates_dir));
        }

        // Load all TOML files in subdirectories
        for entry in walkdir::WalkDir::new(&templates_path)
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.path().is_file() && 
                e.path().extension().map_or(false, |ext| ext == "toml")
            }) {
            
            let path = entry.path();
            let content = fs::read_to_string(path)
                .with_context(|| format!("Failed to read template file: {:?}", path))?;
            
            let config: TemplateConfig = toml::from_str(&content)
                .with_context(|| format!("Failed to parse template file: {:?}", path))?;
            
            for (name, template) in config.tools {
                self.templates.insert(name, template);
            }
        }

        // Initialize Tera for template rendering
        self.tera.add_raw_templates(vec![
            ("command", "{{ command }} {{ args|join(' ') }}"),
            ("output_file", "{{ output_file }}"),
        ])?;

        Ok(())
    }



    pub fn get_applicable_templates(&self, system_info: &crate::core::detector::SystemInfo) -> Vec<&ToolTemplate> {
        self.templates
            .values()
            .filter(|template| self.is_template_applicable(template, system_info))
            .collect()
    }

    fn is_template_applicable(&self, template: &ToolTemplate, system_info: &crate::core::detector::SystemInfo) -> bool {
        if let Some(ref conditions) = template.conditions {
            // Check OS conditions
            if let Some(ref os_list) = conditions.os {
                let current_os = match system_info.os {
                    crate::core::detector::OS::Linux => "linux",
                    crate::core::detector::OS::Windows => "windows",
                    crate::core::detector::OS::MacOS => "macos",
                    crate::core::detector::OS::Unknown => "unknown",
                };
                
                if !os_list.contains(&current_os.to_string()) {
                    return false;
                }
            }

            // Check sudo requirements
            if let Some(required_sudo) = conditions.has_sudo {
                if required_sudo != system_info.has_sudo {
                    return false;
                }
            }
        }

        true
    }

    pub fn render_command(&self, template: &ToolTemplate, target: &str, port_range: Option<&str>) -> Result<String> {
        let mut context = TeraContext::new();
        context.insert("target", target);
        
        if let Some(ports) = port_range {
            context.insert("port_range", ports);
        }

        // Render arguments
        let rendered_args: Result<Vec<String>> = template
            .args
            .iter()
            .map(|arg| self.render_template_string(arg, &context))
            .collect();
        
        let args = rendered_args?;

        Ok(format!("{} {}", template.command, args.join(" ")))
    }

    pub fn render_output_file(&self, template: &ToolTemplate, target: &str) -> Result<Option<String>> {
        if let Some(ref output_file_template) = template.output_file {
            let mut context = TeraContext::new();
            context.insert("target", target);
            context.insert("tool_name", &template.name);
            
            let rendered = self.render_template_string(output_file_template, &context)?;
            Ok(Some(rendered))
        } else {
            Ok(None)
        }
    }

    fn render_template_string(&self, template_str: &str, context: &TeraContext) -> Result<String> {
        // Simple template rendering for common patterns
        let mut result = template_str.to_string();
        
        // Replace common variables
        result = result.replace("{target}", &context.get("target").unwrap_or(&tera::Value::String("".to_string())).as_str().unwrap_or(""));
        result = result.replace("{port_range}", &context.get("port_range").unwrap_or(&tera::Value::String("".to_string())).as_str().unwrap_or(""));
        result = result.replace("{tool_name}", &context.get("tool_name").unwrap_or(&tera::Value::String("".to_string())).as_str().unwrap_or(""));
        
        // Replace timestamp
        if result.contains("{timestamp}") {
            let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
            result = result.replace("{timestamp}", &timestamp.to_string());
        }
        
        Ok(result)
    }




}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::detector::{SystemInfo, OS};

    #[test]
    fn test_template_validation() {
        let template = ToolTemplate {
            name: "test".to_string(),
            description: "Test template".to_string(),
            command: "echo".to_string(),
            args: vec!["hello".to_string()],
            output_file: None,
            category: "test".to_string(),
            dependencies: None,
            parse_strategy: "llm".to_string(),
            output_format: "json".to_string(),
            requires_sudo: None,
            timeout_seconds: None,
            max_retries: None,
            conditions: None,
        };

        // This would need a TemplateManager instance to test
        // For now, just test the template structure
        assert_eq!(template.name, "test");
        assert_eq!(template.parse_strategy, "llm");
    }
}