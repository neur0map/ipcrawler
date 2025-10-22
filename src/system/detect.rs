use anyhow::{Context, Result};
use std::process::Command;

pub fn detect_package_manager() -> Option<String> {
    // Check for AUR helpers first (Arch Linux User Repository)
    // These should be preferred over pacman for AUR packages
    let aur_helpers = vec![
        ("yay", "yay"),
        ("paru", "paru"),
        ("pikaur", "pikaur"),
        ("trizen", "trizen"),
    ];

    // Check if we're on an Arch-based system by checking for pacman
    if check_command_exists("pacman") {
        // Try to find an AUR helper first
        for (name, binary) in aur_helpers {
            if check_command_exists(binary) {
                return Some(name.to_string());
            }
        }
        // Fall back to pacman if no AUR helper found
        return Some("pacman".to_string());
    }

    // Check other package managers
    let managers = vec![
        ("apt", "apt-get"),
        ("dnf", "dnf"),
        ("yum", "yum"),
        ("zypper", "zypper"),
        ("brew", "brew"),
    ];

    for (name, binary) in managers {
        if check_command_exists(binary) {
            return Some(name.to_string());
        }
    }

    None
}

pub fn check_tool_installed(binary: &str) -> bool {
    check_command_exists(binary)
}

pub fn check_command_exists(command: &str) -> bool {
    Command::new("which")
        .arg(command)
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false)
}

pub fn execute_installer_command(command: &str) -> Result<()> {
    let has_sudo = check_command_exists("sudo");

    let full_command = if has_sudo && needs_sudo(command) {
        format!("sudo {}", command)
    } else {
        command.to_string()
    };

    let output = Command::new("sh")
        .arg("-c")
        .arg(&full_command)
        .output()
        .context("Failed to execute installer command")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let error_msg = if !stderr.is_empty() {
            stderr.to_string()
        } else if !stdout.is_empty() {
            stdout.to_string()
        } else {
            format!("Command exited with status: {:?}", output.status.code())
        };
        anyhow::bail!("Installation failed: {}", error_msg.trim());
    }

    Ok(())
}

fn needs_sudo(command: &str) -> bool {
    // AUR helpers (yay, paru, pikaur, trizen) should NOT be run with sudo
    // They handle privilege escalation internally when needed
    let package_managers = ["apt", "yum", "dnf", "pacman", "zypper"];
    package_managers.iter().any(|pm| command.starts_with(pm))
}

/// Detects if the current process is running with sudo/root privileges
pub fn is_running_as_root() -> bool {
    #[cfg(target_os = "linux")]
    {
        // Check if effective user ID is 0 (root)
        unsafe { libc::geteuid() == 0 }
    }

    #[cfg(target_os = "macos")]
    {
        unsafe { libc::geteuid() == 0 }
    }

    #[cfg(target_os = "windows")]
    {
        // Windows doesn't have the same concept, always return false
        false
    }

    #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
    {
        false
    }
}
