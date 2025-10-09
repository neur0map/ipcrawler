use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Template {
    pub name: String,
    pub description: String,
    pub enabled: Option<bool>,
    pub command: TemplateCommand,
    pub depends_on: Option<Vec<String>>,
    pub outputs: Option<Vec<TemplateOutput>>,
    pub timeout: Option<u64>,
    pub env: Option<HashMap<String, String>>,
    pub requires_sudo: Option<bool>,
    #[serde(default)]
    pub pre_scan: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateCommand {
    pub binary: String,
    pub args: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateOutput {
    pub pattern: String,
}

impl Template {
    pub fn is_enabled(&self) -> bool {
        self.enabled.unwrap_or(true)
    }

    pub fn requires_sudo(&self) -> bool {
        self.requires_sudo.unwrap_or(false)
    }

    pub fn get_timeout(&self) -> u64 {
        self.timeout.unwrap_or(3600)
    }

    pub fn interpolate_args(
        &self,
        target: &str,
        output_dir: &str,
        ports: Option<&str>,
        wordlist: Option<&str>,
    ) -> Vec<String> {
        self.command
            .args
            .iter()
            .flat_map(|arg| {
                let mut result = arg
                    .replace("{{target}}", target)
                    .replace("{{output_dir}}", output_dir);

                if let Some(port_spec) = ports {
                    result = result.replace("{{ports}}", port_spec);
                }

                if let Some(wordlist_path) = wordlist {
                    result = result.replace("{{wordlist}}", wordlist_path);
                }

                // Split on newlines to handle multi-argument replacements
                result
                    .split('\n')
                    .map(|s| s.to_string())
                    .collect::<Vec<_>>()
            })
            .collect()
    }
}
