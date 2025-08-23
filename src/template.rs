use crate::output::ScanSummary;
use minijinja::{Environment, Error as TemplateError};
use serde_json::{json, Value as JsonValue};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

pub struct TemplateEngine {
    env: Environment<'static>,
    templates_dir: PathBuf,
}

#[derive(Debug)]
pub enum OutputFormat {
    Json,
    Text,
    Markdown,
    Html,
}

impl OutputFormat {
    pub fn extension(&self) -> &'static str {
        match self {
            OutputFormat::Json => "json",
            OutputFormat::Text => "txt", 
            OutputFormat::Markdown => "md",
            OutputFormat::Html => "html",
        }
    }

    pub fn template_dir(&self) -> &'static str {
        match self {
            OutputFormat::Json => "json",
            OutputFormat::Text => "txt",
            OutputFormat::Markdown => "markdown", 
            OutputFormat::Html => "html",
        }
    }
}

impl TemplateEngine {
    pub fn new(templates_dir: PathBuf) -> Result<Self, TemplateError> {
        let mut env = Environment::new();
        
        // Add custom filters for recon data - using proper minijinja signatures
        env.add_filter("format_duration", |value: f64| {
            if value < 60.0 {
                format!("{:.1}s", value)
            } else if value < 3600.0 {
                format!("{:.1}m", value / 60.0)
            } else {
                format!("{:.1}h", value / 3600.0)
            }
        });
        
        env.add_filter("format_bytes", |value: u64| {
            if value < 1024 {
                format!("{}B", value)
            } else if value < 1024 * 1024 {
                format!("{:.1}KB", value as f64 / 1024.0)
            } else if value < 1024 * 1024 * 1024 {
                format!("{:.1}MB", value as f64 / (1024.0 * 1024.0))
            } else {
                format!("{:.1}GB", value as f64 / (1024.0 * 1024.0 * 1024.0))
            }
        });
        
        // Load templates from filesystem
        let engine = Self {
            env,
            templates_dir,
        };
        
        engine.load_templates()?;
        Ok(engine)
    }

    fn load_templates(&self) -> Result<(), TemplateError> {
        // This will be expanded to load templates from filesystem
        // For now, we'll use embedded templates
        Ok(())
    }

    pub fn render_summary(
        &mut self,
        summary: &ScanSummary,
        format: OutputFormat,
        template_name: Option<&str>,
    ) -> Result<String, TemplateError> {
        let template_name = template_name.unwrap_or("summary");
        let _template_id = format!("{}-{}", format.template_dir(), template_name);

        // Create template context
        let context = self.create_template_context(summary);

        // Try to load template from file, fallback to embedded
        let template_content = {
            let template_path = format!("{}/{}.{}.j2", 
                format.template_dir(), 
                template_name,
                format.extension()
            );
            self.load_template_content(&template_path)
                .unwrap_or_else(|_| self.get_embedded_template(&format, template_name))
        };

        let template = self.env.template_from_str(&template_content)?;
        template.render(&context)
    }

    fn load_template_content(&self, template_path: &str) -> Result<String, std::io::Error> {
        let full_path = self.templates_dir.join(template_path);
        fs::read_to_string(full_path)
    }

    fn get_embedded_template(&self, format: &OutputFormat, template_name: &str) -> String {
        match (format, template_name) {
            (OutputFormat::Json, "summary") => include_str!("../templates/json/summary.json.j2").to_string(),
            (OutputFormat::Text, "summary") => include_str!("../templates/txt/summary.txt.j2").to_string(),
            (OutputFormat::Markdown, "summary") => include_str!("../templates/markdown/summary.md.j2").to_string(),
            (OutputFormat::Html, "summary") => include_str!("../templates/html/summary.html.j2").to_string(),
            _ => self.get_default_template(format),
        }
    }

    fn get_default_template(&self, format: &OutputFormat) -> String {
        match format {
            OutputFormat::Json => r#"{{ summary | tojson }}"#.to_string(),
            OutputFormat::Text => include_str!("../templates/txt/default.txt.j2").to_string(),
            OutputFormat::Markdown => include_str!("../templates/markdown/default.md.j2").to_string(),
            OutputFormat::Html => include_str!("../templates/html/default.html.j2").to_string(),
        }
    }

    fn create_template_context(&self, summary: &ScanSummary) -> JsonValue {
        // Convert summary to JSON and add helper data
        let mut context = json!(summary);
        
        // Add computed fields for templates
        if let Some(context_obj) = context.as_object_mut() {
            // Group discoveries by type
            let discoveries_by_type = self.group_discoveries_by_type(summary);
            context_obj.insert("discoveries_by_type".to_string(), json!(discoveries_by_type));
            
            // Add convenience fields
            context_obj.insert("ports_count".to_string(), json!(
                summary.discoveries.iter()
                    .filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Port { .. }))
                    .count()
            ));
            
            context_obj.insert("services_count".to_string(), json!(
                summary.discoveries.iter()
                    .filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Service { .. }))
                    .count()
            ));

            // Add template generation metadata
            context_obj.insert("template_generated_at".to_string(), json!(chrono::Utc::now().to_rfc3339()));
        }
        
        context
    }

    fn group_discoveries_by_type<'a>(&self, summary: &'a ScanSummary) -> HashMap<String, Vec<&'a crate::output::Discovery>> {
        let mut grouped = HashMap::new();
        
        for discovery in &summary.discoveries {
            let type_key = match &discovery.discovery_type {
                crate::output::DiscoveryType::Port { .. } => "ports",
                crate::output::DiscoveryType::Service { .. } => "services", 
                crate::output::DiscoveryType::Host { .. } => "hosts",
                crate::output::DiscoveryType::Vulnerability { .. } => "vulnerabilities",
                crate::output::DiscoveryType::Directory { .. } => "directories",
                crate::output::DiscoveryType::Custom { category, .. } => category.as_str(),
            };
            
            grouped.entry(type_key.to_string()).or_insert_with(Vec::new).push(discovery);
        }
        
        grouped
    }
}

// The custom filters are now implemented inline in the TemplateEngine::new method