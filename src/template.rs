use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ToolTemplate {
    pub name: String,
    pub description: String,
    pub command: String,
    pub args: Vec<String>,
    pub output_file: Option<String>,
    pub category: String,
    pub dependencies: Option<Vec<String>>,
}

#[derive(Debug, Deserialize)]
pub struct TemplateConfig {
    pub tools: HashMap<String, ToolTemplate>,
}

pub struct TemplateManager {
    templates: HashMap<String, ToolTemplate>,
    templates_dir: String,
}

impl TemplateManager {
    pub fn new(templates_dir: &str) -> Result<Self> {
        let mut manager = TemplateManager {
            templates: HashMap::new(),
            templates_dir: templates_dir.to_string(),
        };
        
        manager.load_templates()?;
        Ok(manager)
    }
    
    fn load_templates(&mut self) -> Result<()> {
        let templates_path = Path::new(&self.templates_dir);
        
        if !templates_path.exists() {
            return Err(anyhow::anyhow!("Templates directory not found: {}", self.templates_dir));
        }
        
        for entry in fs::read_dir(templates_path)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                self.load_category_templates(&path)?;
            } else if path.extension().and_then(|s| s.to_str()) == Some("yaml") 
                   || path.extension().and_then(|s| s.to_str()) == Some("toml") {
                self.load_template_file(&path)?;
            }
        }
        
        Ok(())
    }
    
    fn load_category_templates(&mut self, category_path: &Path) -> Result<()> {
        for entry in fs::read_dir(category_path)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("yaml")
               || path.extension().and_then(|s| s.to_str()) == Some("toml") {
                self.load_template_file(&path)?;
            }
        }
        Ok(())
    }
    
    fn load_template_file(&mut self, file_path: &Path) -> Result<()> {
        let content = fs::read_to_string(file_path)
            .with_context(|| format!("Failed to read template file: {:?}", file_path))?;
        
        let template_config: TemplateConfig = toml::from_str(&content)
            .with_context(|| format!("Failed to parse TOML template: {:?}", file_path))?;
        
        for (name, mut template) in template_config.tools {
            // Set category based on file location if not specified
            if template.category.is_empty() {
                if let Some(parent) = file_path.parent() {
                    if let Some(category_name) = parent.file_name() {
                        template.category = category_name.to_string_lossy().to_string();
                    }
                }
            }
            
            self.templates.insert(name, template);
        }
        
        Ok(())
    }
    
    pub fn get_all_templates(&self) -> Vec<&ToolTemplate> {
        self.templates.values().collect()
    }
    
    #[allow(dead_code)]
    pub fn get_templates_by_category(&self, category: &str) -> Vec<&ToolTemplate> {
        self.templates
            .values()
            .filter(|template| template.category == category)
            .collect()
    }
    
    #[allow(dead_code)]
    pub fn get_template(&self, name: &str) -> Option<&ToolTemplate> {
        self.templates.get(name)
    }
}
