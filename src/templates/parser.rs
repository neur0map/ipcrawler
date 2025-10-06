use super::models::Template;
use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};
use tracing::{debug, warn};

pub struct TemplateParser {
    templates_dir: PathBuf,
}

impl TemplateParser {
    pub fn new(templates_dir: PathBuf) -> Self {
        Self { templates_dir }
    }

    pub fn load_all(&self) -> Result<Vec<Template>> {
        if !self.templates_dir.exists() {
            anyhow::bail!(
                "Templates directory does not exist: {}",
                self.templates_dir.display()
            );
        }

        let mut templates = Vec::new();
        let entries = fs::read_dir(&self.templates_dir)
            .context("Failed to read templates directory")?;

        for entry in entries {
            let entry = entry?;
            let path = entry.path();

            if path.extension().and_then(|s| s.to_str()) == Some("yaml") {
                match self.load_template(&path) {
                    Ok(template) => {
                        debug!("Loaded template: {}", template.name);
                        templates.push(template);
                    }
                    Err(e) => {
                        warn!("Failed to load template {:?}: {}", path, e);
                    }
                }
            }
        }

        Ok(templates)
    }

    pub fn load_template(&self, path: &Path) -> Result<Template> {
        let content = fs::read_to_string(path)
            .with_context(|| format!("Failed to read template file: {}", path.display()))?;

        let template: Template = serde_yaml::from_str(&content)
            .with_context(|| format!("Failed to parse template: {}", path.display()))?;

        Ok(template)
    }

    pub fn find_template(&self, name: &str) -> Result<Template> {
        let yaml_path = self.templates_dir.join(format!("{}.yaml", name));
        
        if yaml_path.exists() {
            self.load_template(&yaml_path)
        } else {
            anyhow::bail!("Template not found: {}", name)
        }
    }
}
