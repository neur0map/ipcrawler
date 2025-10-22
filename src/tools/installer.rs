use crate::config::Tool;
use crate::system::{check_tool_installed, detect_package_manager, execute_installer_command};
use anyhow::{Context, Result};
use std::io::{self, Write};

pub struct ToolInstaller {
    package_manager: Option<String>,
    auto_install: bool,
}

impl ToolInstaller {
    pub fn new(auto_install: bool) -> Self {
        let package_manager = detect_package_manager();
        Self {
            package_manager,
            auto_install,
        }
    }

    pub fn ensure_tool_installed(&self, tool: &Tool) -> Result<bool> {
        let tool_binary = self.extract_binary_name(&tool.command);

        if check_tool_installed(&tool_binary) {
            return Ok(true);
        }

        if self.auto_install {
            self.install_tool(tool, &tool_binary)?;
            return Ok(check_tool_installed(&tool_binary));
        }

        self.prompt_and_install(tool, &tool_binary)
    }

    fn extract_binary_name(&self, command: &str) -> String {
        command.split_whitespace().next().unwrap_or("").to_string()
    }

    fn install_tool(&self, tool: &Tool, _binary: &str) -> Result<()> {
        let package_manager = self
            .package_manager
            .as_deref()
            .context("No supported package manager found on this system")?;

        let install_cmd = tool
            .get_installer_command(package_manager)
            .with_context(|| {
                format!(
                    "No installer command found for tool '{}' with package manager '{}'",
                    tool.name, package_manager
                )
            })?;

        let has_sudo = crate::system::detect::check_command_exists("sudo");
        let needs_sudo = ["apt", "yum", "dnf", "pacman", "zypper"]
            .iter()
            .any(|pm| install_cmd.starts_with(pm));

        if has_sudo && needs_sudo {
            println!("Installing {} using: sudo {}", tool.name, install_cmd);
        } else {
            println!("Installing {} using: {}", tool.name, install_cmd);
        }

        execute_installer_command(&install_cmd)?;

        println!("Successfully installed {}", tool.name);

        Ok(())
    }

    fn prompt_and_install(&self, tool: &Tool, binary: &str) -> Result<bool> {
        let package_manager = match &self.package_manager {
            Some(pm) => pm,
            None => {
                eprintln!(
                    "Tool '{}' (binary: {}) not found and no supported package manager detected.",
                    tool.name, binary
                );
                eprintln!("Please install it manually.");
                return Ok(false);
            }
        };

        let install_cmd = match tool.get_installer_command(package_manager) {
            Some(cmd) => cmd,
            None => {
                eprintln!(
                    "Tool '{}' (binary: {}) not found. No installer command available for package manager '{}'.",
                    tool.name, binary, package_manager
                );
                eprintln!("Please install it manually.");
                return Ok(false);
            }
        };

        print!(
            "Tool '{}' not found. Install using: {}? [y/N] ",
            tool.name, install_cmd
        );
        io::stdout().flush()?;

        let mut response = String::new();
        io::stdin().read_line(&mut response)?;

        let response = response.trim().to_lowercase();
        if response == "y" || response == "yes" {
            self.install_tool(tool, binary)?;
            Ok(check_tool_installed(binary))
        } else {
            println!("Skipping installation of {}", tool.name);
            Ok(false)
        }
    }

    #[allow(dead_code)]
    pub fn check_all_tools(&self, tools: &[&Tool]) -> Vec<(String, bool)> {
        tools
            .iter()
            .map(|tool| {
                let binary = self.extract_binary_name(&tool.command);
                let installed = check_tool_installed(&binary);
                (tool.name.clone(), installed)
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_binary_name() {
        let installer = ToolInstaller::new(false);

        assert_eq!(installer.extract_binary_name("nmap -sV {target}"), "nmap");
        assert_eq!(installer.extract_binary_name("nikto -h {target}"), "nikto");
    }
}
