use crate::config::Tool;
use crate::system::{
    check_tool_installed, detect_package_manager, execute_installer_command, is_running_as_root,
};
use anyhow::{Context, Result};
use std::io::{self, Write};
use std::process::Command;
use std::thread;
use std::time::Duration;

pub struct ToolInstaller {
    package_manager: Option<String>,
}

impl ToolInstaller {
    pub fn new() -> Self {
        let package_manager = detect_package_manager();
        Self { package_manager }
    }

    pub fn ensure_sudo_access(&self) -> Result<()> {
        if is_running_as_root() {
            return Ok(());
        }

        // Check if we can use sudo
        let output = Command::new("sudo")
            .arg("-n")
            .arg("true")
            .output()
            .context("Failed to check sudo access")?;

        if !output.status.success() {
            println!("SECURITY: This installation requires sudo privileges.");
            print!("Please enter your sudo password: ");
            io::stdout().flush()?;

            // Validate sudo access by asking for password
            let output = Command::new("sudo")
                .arg("true")
                .output()
                .context("Failed to validate sudo access")?;

            if !output.status.success() {
                anyhow::bail!(
                    "Sudo authentication failed. Please check your password and try again."
                );
            }

            println!("SUCCESS: Sudo access validated");
        }

        Ok(())
    }

    pub fn start_sudo_keep_alive(&self) -> Result<()> {
        if is_running_as_root() {
            return Ok(());
        }

        println!("INFO: Starting sudo keep-alive for batch installation...");

        // Start a background process to keep sudo alive
        thread::spawn(|| {
            loop {
                let _ = Command::new("sudo").arg("-n").arg("true").output();

                thread::sleep(Duration::from_secs(60)); // Refresh every minute
            }
        });

        Ok(())
    }

    pub fn install_tool(&self, tool: &Tool, _binary: &str) -> Result<()> {
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

        // AUR helpers (yay, paru, pikaur, trizen) should NOT be run with sudo
        // They handle privilege escalation internally when needed
        let needs_sudo = ["apt", "yum", "dnf", "pacman", "zypper"]
            .iter()
            .any(|pm| install_cmd.starts_with(pm));

        if needs_sudo && !is_running_as_root() {
            self.ensure_sudo_access()?;
        }

        println!("Installing {} using: {}", tool.name, install_cmd);

        execute_installer_command(&install_cmd)?;

        // Note: Verification happens in the caller (checker.rs)
        Ok(())
    }

    pub fn prompt_and_install(&self, tool: &Tool, binary: &str) -> Result<bool> {
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
}
