use anyhow::{Context, Result};
use std::env;
use std::path::PathBuf;
use std::process::Command;

#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub enum OperatingSystem {
    Linux,
    MacOS,
    Windows,
    Unknown,
}

#[allow(dead_code)]
impl OperatingSystem {
    pub fn as_str(&self) -> &'static str {
        match self {
            OperatingSystem::Linux => "linux",
            OperatingSystem::MacOS => "macos",
            OperatingSystem::Windows => "windows",
            OperatingSystem::Unknown => "unknown",
        }
    }
}

#[allow(dead_code)]
pub fn detect_os() -> OperatingSystem {
    match env::consts::OS {
        "linux" => OperatingSystem::Linux,
        "macos" => OperatingSystem::MacOS,
        "windows" => OperatingSystem::Windows,
        _ => OperatingSystem::Unknown,
    }
}

pub fn detect_package_manager() -> Option<String> {
    let managers = vec![
        ("apt", "apt-get"),
        ("dnf", "dnf"),
        ("yum", "yum"),
        ("pacman", "pacman"),
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

#[allow(dead_code)]
pub fn get_install_paths() -> Vec<PathBuf> {
    let mut paths = vec![
        PathBuf::from("/usr/bin"),
        PathBuf::from("/usr/local/bin"),
        PathBuf::from("/bin"),
        PathBuf::from("/usr/sbin"),
        PathBuf::from("/sbin"),
    ];

    if let Ok(home) = env::var("HOME") {
        paths.push(PathBuf::from(home).join(".local/bin"));
    }

    if let Ok(path_env) = env::var("PATH") {
        for path in path_env.split(':') {
            let path_buf = PathBuf::from(path);
            if !paths.contains(&path_buf) {
                paths.push(path_buf);
            }
        }
    }

    paths
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_os() {
        let os = detect_os();
        assert_ne!(os, OperatingSystem::Unknown);
    }

    #[test]
    fn test_get_install_paths() {
        let paths = get_install_paths();
        assert!(!paths.is_empty());
    }
}
