use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Template {
    pub name: String,
    pub description: String,
    #[serde(default = "default_enabled")]
    pub enabled: bool,
    pub command: Command,
    #[serde(default)]
    pub depends_on: Vec<String>,
    pub outputs: Vec<OutputPattern>,
    #[serde(default = "default_timeout")]
    pub timeout: u64,
    #[serde(default)]
    pub env: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Command {
    pub binary: String,
    pub args: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutputPattern {
    pub pattern: String,
}

fn default_enabled() -> bool {
    true
}

fn default_timeout() -> u64 {
    3600
}

impl Template {
    pub fn substitute_variables(&self, target: &str, output_dir: &str) -> Self {
        let mut template = self.clone();
        
        template.command.args = template
            .command
            .args
            .iter()
            .map(|arg| {
                arg.replace("{{target}}", target)
                    .replace("{{output_dir}}", output_dir)
                    .replace("{{template_name}}", &self.name)
            })
            .collect();
        
        template.outputs = template
            .outputs
            .iter()
            .map(|output| OutputPattern {
                pattern: output
                    .pattern
                    .replace("{{target}}", target)
                    .replace("{{output_dir}}", output_dir)
                    .replace("{{template_name}}", &self.name),
            })
            .collect();
        
        template
    }
}
