use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};
use super::models::Template;

pub struct TemplateParser {
    templates_dir: PathBuf,
}

impl TemplateParser {
    pub fn new(templates_dir: PathBuf) -> Self {
        Self { templates_dir }
    }
    
    pub fn load_all(&self) -> Result<Vec<Template>> {
        let mut templates = Vec::new();
        
        if !self.templates_dir.exists() {
            return Ok(templates);
        }
        
        for entry in fs::read_dir(&self.templates_dir)
            .context("Failed to read templates directory")?
        {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("yaml")
                || path.extension().and_then(|s| s.to_str()) == Some("yml")
            {
                match self.load_template(&path) {
                    Ok(template) => {
                        if template.enabled {
                            templates.push(template);
                        }
                    }
                    Err(e) => {
                        tracing::warn!("Failed to load template {:?}: {}", path, e);
                    }
                }
            }
        }
        
        Ok(templates)
    }
    
    pub fn load_template(&self, path: &Path) -> Result<Template> {
        let content = fs::read_to_string(path)
            .with_context(|| format!("Failed to read template file: {:?}", path))?;
        
        let template: Template = serde_yaml::from_str(&content)
            .with_context(|| format!("Failed to parse template: {:?}", path))?;
        
        Ok(template)
    }
    
    pub fn load_by_name(&self, name: &str) -> Result<Template> {
        let yaml_path = self.templates_dir.join(format!("{}.yaml", name));
        let yml_path = self.templates_dir.join(format!("{}.yml", name));
        
        if yaml_path.exists() {
            self.load_template(&yaml_path)
        } else if yml_path.exists() {
            self.load_template(&yml_path)
        } else {
            anyhow::bail!("Template '{}' not found", name)
        }
    }
}
