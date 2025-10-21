use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Tool {
    pub name: String,
    pub description: String,
    pub command: String,
    pub installer: InstallerConfig,
    #[serde(default = "default_timeout")]
    pub timeout: u64,
    pub output: OutputConfig,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct InstallerConfig {
    #[serde(default)]
    pub apt: Option<String>,
    #[serde(default)]
    pub yum: Option<String>,
    #[serde(default)]
    pub dnf: Option<String>,
    #[serde(default)]
    pub brew: Option<String>,
    #[serde(default)]
    pub pacman: Option<String>,
    #[serde(default)]
    pub zypper: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OutputConfig {
    #[serde(rename = "type")]
    pub output_type: OutputType,
    #[serde(default)]
    pub json_flag: Option<String>,
    #[serde(default)]
    pub patterns: Vec<Pattern>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum OutputType {
    Json,
    Xml,
    Regex,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Pattern {
    pub name: String,
    pub regex: String,
    #[serde(default = "default_severity")]
    pub severity: Severity,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

impl Severity {
    pub fn as_str(&self) -> &'static str {
        match self {
            Severity::Info => "INFO",
            Severity::Low => "LOW",
            Severity::Medium => "MEDIUM",
            Severity::High => "HIGH",
            Severity::Critical => "CRITICAL",
        }
    }
}

fn default_timeout() -> u64 {
    300
}

fn default_severity() -> Severity {
    Severity::Info
}

impl Tool {
    pub fn get_installer_command(&self, package_manager: &str) -> Option<String> {
        match package_manager {
            "apt" => self.installer.apt.clone(),
            "yum" => self.installer.yum.clone(),
            "dnf" => self.installer.dnf.clone(),
            "brew" => self.installer.brew.clone(),
            "pacman" => self.installer.pacman.clone(),
            "zypper" => self.installer.zypper.clone(),
            _ => None,
        }
    }

    pub fn render_command(
        &self,
        target: &str,
        port: Option<u16>,
        output_file: &str,
    ) -> anyhow::Result<String> {
        let mut context = HashMap::new();
        context.insert("target", target.to_string());
        context.insert("output_file", output_file.to_string());

        if let Some(p) = port {
            context.insert("port", p.to_string());
        }

        let handlebars = handlebars::Handlebars::new();
        let rendered = handlebars.render_template(&self.command, &context)?;

        Ok(rendered)
    }
}
