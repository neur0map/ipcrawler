use crate::config::Tool;
use crate::system::check_tool_installed;
use crate::tools::installer::ToolInstaller;
use anyhow::Result;
use std::io::{self, Write};

pub struct ToolAvailabilityReport {
    pub tools: Vec<ToolStatus>,
    pub missing_count: usize,
    pub total_count: usize,
}

#[derive(Debug, Clone)]
pub struct ToolStatus {
    pub name: String,
    pub binary: String,
    pub installed: bool,
    pub tool: Tool,
}

pub struct ToolChecker {
    installer: ToolInstaller,
}

impl ToolChecker {
    pub fn new() -> Self {
        Self {
            installer: ToolInstaller::new(),
        }
    }

    pub fn check_all_tools(&self, tools: &[&Tool]) -> ToolAvailabilityReport {
        let mut tool_statuses = Vec::new();
        let mut missing_count = 0;

        for tool in tools {
            let (binary, installed) = self.check_tool_availability(tool);

            if !installed {
                missing_count += 1;
            }

            tool_statuses.push(ToolStatus {
                name: tool.name.clone(),
                binary,
                installed,
                tool: (*tool).clone(),
            });
        }

        ToolAvailabilityReport {
            tools: tool_statuses,
            missing_count,
            total_count: tools.len(),
        }
    }

    fn check_tool_availability(&self, tool: &Tool) -> (String, bool) {
        // Check if it's a script tool
        if let Some(script_path) = &tool.script_path {
            let script_name = format!("{}.sh", tool.name);
            let script_exists = std::path::Path::new(script_path).exists()
                || std::path::Path::new(&format!("tools/scripts/{}", script_name)).exists()
                || check_tool_installed(&script_name);

            if script_exists {
                return (script_name, true);
            }
        }

        // Check if command references a script
        let binary = self.extract_binary_name(&tool.command);
        if binary.ends_with(".sh") {
            let script_path = format!("tools/scripts/{}", binary);
            if std::path::Path::new(&script_path).exists() {
                return (binary, true);
            }
        }

        // For script tools, also check if their dependencies are available
        if self.is_script_tool(tool) {
            let dependencies = self.get_tool_dependencies(tool);
            let all_deps_available = dependencies.iter().all(|dep| check_tool_installed(dep));
            return (binary, all_deps_available);
        }

        // Default: check as binary
        (binary.clone(), check_tool_installed(&binary))
    }

    fn is_script_tool(&self, tool: &Tool) -> bool {
        tool.command.ends_with(".sh")
            || tool.command.contains("{{target}} {{port}} {{output_file}}")
    }

    fn get_tool_dependencies(&self, tool: &Tool) -> Vec<String> {
        let mut dependencies = Vec::new();

        // Extract dependencies from installer commands
        if let Some(apt_cmd) = &tool.installer.apt {
            dependencies.extend(self.extract_packages_from_command(apt_cmd));
        }
        if let Some(pacman_cmd) = &tool.installer.pacman {
            dependencies.extend(self.extract_packages_from_command(pacman_cmd));
        }
        if let Some(yum_cmd) = &tool.installer.yum {
            dependencies.extend(self.extract_packages_from_command(yum_cmd));
        }
        if let Some(dnf_cmd) = &tool.installer.dnf {
            dependencies.extend(self.extract_packages_from_command(dnf_cmd));
        }

        dependencies
    }

    fn extract_packages_from_command(&self, command: &str) -> Vec<String> {
        // Extract package names from install commands
        if command.contains("pacman -S") {
            command
                .split_whitespace()
                .skip(3) // Skip "pacman -S --noconfirm"
                .take_while(|pkg| !pkg.starts_with('-'))
                .map(|s| s.to_string())
                .collect()
        } else if command.contains("apt install") {
            command
                .split_whitespace()
                .skip(2) // Skip "apt install -y"
                .map(|s| s.to_string())
                .collect()
        } else if command.contains("yum install") || command.contains("dnf install") {
            command
                .split_whitespace()
                .skip(2) // Skip "yum/dnf install -y"
                .map(|s| s.to_string())
                .collect()
        } else {
            Vec::new()
        }
    }

    pub fn prompt_install_all(&self, report: &ToolAvailabilityReport) -> Result<bool> {
        if report.missing_count == 0 {
            println!("SUCCESS: All tools are already installed!");
            return Ok(true);
        }

        println!("\nTool Availability Report:");
        println!("   Total tools: {}", report.total_count);
        println!("   Missing: {} (MISSING)", report.missing_count);
        println!(
            "   Installed: {} (AVAILABLE)",
            report.total_count - report.missing_count
        );

        println!("\nMissing tools:");
        for status in &report.tools {
            if !status.installed {
                println!("   - {} (binary: {})", status.name, status.binary);
            }
        }

        print!("\nInstall all missing tools? [y/N] ");
        io::stdout().flush()?;

        let mut response = String::new();
        io::stdin().read_line(&mut response)?;

        let response = response.trim().to_lowercase();
        Ok(response == "y" || response == "yes")
    }

    pub fn install_missing_tools(&self, report: &ToolAvailabilityReport) -> Result<Vec<String>> {
        let mut successfully_installed = Vec::new();
        let mut failed_installs = Vec::new();

        // Check if any tools need sudo and start keep-alive if needed
        let needs_sudo = report
            .tools
            .iter()
            .any(|status| !status.installed && self.tool_needs_sudo(&status.tool));

        if needs_sudo {
            if let Err(e) = self.installer.ensure_sudo_access() {
                println!("ERROR: Failed to get sudo access: {}", e);
                return Ok(vec![]);
            }
            if let Err(e) = self.installer.start_sudo_keep_alive() {
                println!("WARNING: Failed to start sudo keep-alive: {}", e);
            }
        }

        println!("\nInstalling missing tools...");

        for status in &report.tools {
            if !status.installed {
                println!("\nInstalling {}...", status.name);
                match self.installer.install_tool(&status.tool, &status.binary) {
                    Ok(()) => {
                        // Verify installation based on tool type
                        let is_available =
                            self.verify_tool_installation(&status.tool, &status.binary);
                        if is_available {
                            println!("SUCCESS: {} installed successfully", status.name);
                            successfully_installed.push(status.name.clone());
                        } else {
                            println!(
                                "ERROR: {} installation failed (tool not found after install)",
                                status.name
                            );
                            failed_installs.push(status.name.clone());
                        }
                    }
                    Err(e) => {
                        println!("ERROR: Failed to install {}: {}", status.name, e);
                        failed_installs.push(status.name.clone());
                    }
                }
            }
        }

        if !failed_installs.is_empty() {
            println!(
                "\nWARNING: Failed to install: {}",
                failed_installs.join(", ")
            );
        }

        if !successfully_installed.is_empty() {
            println!(
                "\nSUCCESS: Successfully installed: {}",
                successfully_installed.join(", ")
            );
        }

        Ok(successfully_installed)
    }

    fn tool_needs_sudo(&self, tool: &Tool) -> bool {
        if let Some(installer_cmd) = tool
            .installer
            .apt
            .as_ref()
            .or(tool.installer.yum.as_ref())
            .or(tool.installer.dnf.as_ref())
            .or(tool.installer.pacman.as_ref())
            .or(tool.installer.zypper.as_ref())
            .or(tool.installer.yay.as_ref())
            .or(tool.installer.paru.as_ref())
            .or(tool.installer.pikaur.as_ref())
            .or(tool.installer.trizen.as_ref())
        {
            // AUR helpers (yay, paru, pikaur, trizen) should NOT be run with sudo
            ["apt", "yum", "dnf", "pacman", "zypper"]
                .iter()
                .any(|pm| installer_cmd.starts_with(pm))
        } else {
            false
        }
    }

    pub fn prompt_individual_installs(&self, report: &ToolAvailabilityReport) -> Result<()> {
        if report.missing_count == 0 {
            return Ok(());
        }

        println!("\nIndividual Tool Installation:");

        for status in &report.tools {
            if !status.installed {
                let installed = self
                    .installer
                    .prompt_and_install(&status.tool, &status.binary)?;
                if installed {
                    println!("SUCCESS: {} is now available", status.name);
                } else {
                    println!("WARNING: {} is still missing", status.name);
                }
            }
        }

        Ok(())
    }

    fn extract_binary_name(&self, command: &str) -> String {
        command.split_whitespace().next().unwrap_or("").to_string()
    }

    fn verify_tool_installation(&self, tool: &Tool, binary: &str) -> bool {
        // For script tools, check if script exists and dependencies are available
        if self.is_script_tool(tool) {
            // Check if script exists
            if binary.ends_with(".sh") {
                let script_path = format!("tools/scripts/{}", binary);
                if !std::path::Path::new(&script_path).exists() {
                    return false;
                }
            }

            // Check dependencies
            let dependencies = self.get_tool_dependencies(tool);
            return dependencies.iter().all(|dep| check_tool_installed(dep));
        }

        // For binary tools, check if binary is available
        check_tool_installed(binary)
    }

    pub fn get_installation_summary(&self, report: &ToolAvailabilityReport) -> String {
        if report.missing_count == 0 {
            "All tools are installed and ready!".to_string()
        } else {
            format!(
                "{} of {} tools are missing. Scan may have limited results.",
                report.missing_count, report.total_count
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::schema::{InstallerConfig, OutputConfig};
    use crate::config::{Tool};
    use crate::config::schema::OutputType;

    fn create_test_tool(name: &str, command: &str) -> Tool {
        Tool {
            name: name.to_string(),
            description: format!("Test tool {}", name),
            command: command.to_string(),
            sudo_command: None,
            script_path: None,
            installer: InstallerConfig {
                apt: Some(format!("apt install {}", name)),
                yum: None,
                dnf: None,
                brew: None,
                pacman: None,
                zypper: None,
                yay: None,
                paru: None,
                pikaur: None,
                trizen: None,
            },
            timeout: 60,
            output: OutputConfig {
                output_type: OutputType::Raw,
                json_flag: None,
            },
        }
    }

    #[test]
    fn test_extract_binary_name() {
        let checker = ToolChecker::new();
        assert_eq!(checker.extract_binary_name("nmap -sV {target}"), "nmap");
        assert_eq!(
            checker.extract_binary_name("gobuster dir -u {target}"),
            "gobuster"
        );
        assert_eq!(checker.extract_binary_name("nikto -h {target}"), "nikto");
    }

    #[test]
    fn test_check_all_tools() {
        let checker = ToolChecker::new();
        let tool1 = create_test_tool("nmap", "nmap {target}");
        let tool2 = create_test_tool("nikto", "nikto -h {target}");
        let tools = vec![&tool1, &tool2];

        let report = checker.check_all_tools(&tools);
        assert_eq!(report.total_count, 2);
        assert_eq!(report.tools.len(), 2);
    }
}
