use crate::config::Tool;
use anyhow::{Context, Result};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub struct ToolRegistry {
    tools: HashMap<String, Tool>,
    tools_dir: PathBuf,
}

impl ToolRegistry {
    pub fn new<P: AsRef<Path>>(tools_dir: P) -> Self {
        Self {
            tools: HashMap::new(),
            tools_dir: tools_dir.as_ref().to_path_buf(),
        }
    }

    pub fn discover_tools(&mut self) -> Result<usize> {
        if !self.tools_dir.exists() {
            fs::create_dir_all(&self.tools_dir)
                .context("Failed to create tools directory")?;
            return Ok(0);
        }

        let entries = fs::read_dir(&self.tools_dir)
            .context("Failed to read tools directory")?;

        let mut count = 0;
        for entry in entries {
            let entry = entry?;
            let path = entry.path();

            if path.extension().and_then(|s| s.to_str()) == Some("yaml")
                || path.extension().and_then(|s| s.to_str()) == Some("yml") {
                match self.load_tool(&path) {
                    Ok(tool) => {
                        self.tools.insert(tool.name.clone(), tool);
                        count += 1;
                    }
                    Err(e) => {
                        eprintln!("Warning: Failed to load tool from {:?}: {}", path, e);
                    }
                }
            }
        }

        Ok(count)
    }

    fn load_tool(&self, path: &Path) -> Result<Tool> {
        let content = fs::read_to_string(path)
            .with_context(|| format!("Failed to read tool file: {:?}", path))?;

        let tool: Tool = serde_yaml::from_str(&content)
            .with_context(|| format!("Failed to parse YAML from {:?}", path))?;

        self.validate_tool(&tool)?;

        Ok(tool)
    }

    fn validate_tool(&self, tool: &Tool) -> Result<()> {
        if tool.name.is_empty() {
            anyhow::bail!("Tool name cannot be empty");
        }

        if tool.command.is_empty() {
            anyhow::bail!("Tool command cannot be empty");
        }

        Ok(())
    }

    pub fn get_tool(&self, name: &str) -> Option<&Tool> {
        self.tools.get(name)
    }

    pub fn get_all_tools(&self) -> Vec<&Tool> {
        self.tools.values().collect()
    }

    #[allow(dead_code)]
    pub fn get_tool_names(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    #[allow(dead_code)]
    pub fn tool_count(&self) -> usize {
        self.tools.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Write;
    use tempfile::tempdir;

    #[test]
    fn test_empty_registry() {
        let dir = tempdir().unwrap();
        let registry = ToolRegistry::new(dir.path());
        assert_eq!(registry.tool_count(), 0);
    }

    #[test]
    fn test_load_valid_tool() {
        let dir = tempdir().unwrap();
        let tool_path = dir.path().join("test.yaml");

        let yaml_content = r#"
name: "test-tool"
description: "Test tool"
command: "test {target}"
installer:
  apt: "apt install test"
timeout: 60
output:
  type: "json"
"#;

        let mut file = File::create(&tool_path).unwrap();
        file.write_all(yaml_content.as_bytes()).unwrap();

        let mut registry = ToolRegistry::new(dir.path());
        let count = registry.discover_tools().unwrap();

        assert_eq!(count, 1);
        assert!(registry.get_tool("test-tool").is_some());
    }
}
