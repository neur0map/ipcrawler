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

/// Get the full path to a command, useful when running as root to access user-installed tools
pub fn get_command_path(command: &str) -> Option<String> {
    // First try with current PATH using which
    if let Ok(output) = Command::new("which").arg(command).output() {
        if output.status.success() {
            if let Ok(path) = String::from_utf8(output.stdout) {
                return Some(path.trim().to_string());
            }
        }
    }

    // If running as root/sudo, search common user bin locations
    if is_running_as_root() {
        if let Ok(user) = std::env::var("SUDO_USER") {
            let search_paths = vec![
                format!("/home/{}/.local/bin/{}", user, command),
                format!("/home/{}/.cargo/bin/{}", user, command),
            ];

            // Check mise/asdf/rtx installations with nested structure: installs/RUNTIME/VERSION/bin
            if let Ok(entries) =
                std::fs::read_dir(format!("/home/{}/.local/share/mise/installs", user))
            {
                for entry in entries.flatten() {
                    let runtime_path = entry.path();
                    if let Ok(version_entries) = std::fs::read_dir(&runtime_path) {
                        for version_entry in version_entries.flatten() {
                            let cmd_path = version_entry.path().join("bin").join(command);
                            if cmd_path.exists() {
                                if let Some(path_str) = cmd_path.to_str() {
                                    return Some(path_str.to_string());
                                }
                            }
                        }
                    }
                }
            }

            // Check standard user paths
            for path in search_paths {
                if std::path::Path::new(&path).exists() {
                    return Some(path);
                }
            }
        }

        // Check system paths
        for base_path in ["/usr/local/bin", "/usr/bin", "/bin"] {
            let full_path = format!("{}/{}", base_path, command);
            if std::path::Path::new(&full_path).exists() {
                return Some(full_path);
            }
        }
    }

    None
}

pub fn check_command_exists(command: &str) -> bool {
    // First try with current PATH
    let result = Command::new("which")
        .arg(command)
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false);

    if result {
        return true;
    }

    // If running as root/sudo, also check common user bin locations
    if is_running_as_root() {
        let sudo_user = std::env::var("SUDO_USER");

        if std::env::var("IPCRAWLER_DEBUG").is_ok() {
            eprintln!("DEBUG: Running as root, SUDO_USER={:?}", sudo_user);
        }

        // Build additional search paths as Strings
        let mut search_paths: Vec<String> = vec![
            "/usr/local/bin".to_string(),
            "/usr/bin".to_string(),
            "/bin".to_string(),
        ];

        // If we know the sudo user, add their common bin paths
        if let Ok(user) = &sudo_user {
            search_paths.push(format!("/home/{}/.local/bin", user));
            search_paths.push(format!("/home/{}/.cargo/bin", user));

            // Check for mise/asdf/rtx installations (common Go tools location)
            let mise_path = format!("/home/{}/.local/share/mise/installs", user);
            if std::env::var("IPCRAWLER_DEBUG").is_ok() {
                eprintln!("DEBUG: Checking mise path: {}", mise_path);
            }

            if let Ok(entries) = std::fs::read_dir(&mise_path) {
                for entry in entries.flatten() {
                    let runtime_path = entry.path();

                    // mise has a nested structure: installs/RUNTIME/VERSION/bin
                    // We need to iterate through version directories too
                    if let Ok(version_entries) = std::fs::read_dir(&runtime_path) {
                        for version_entry in version_entries.flatten() {
                            let bin_path = version_entry.path().join("bin");
                            if bin_path.exists() {
                                let cmd_path = bin_path.join(command);
                                if std::env::var("IPCRAWLER_DEBUG").is_ok() {
                                    eprintln!("DEBUG: Checking {}", cmd_path.display());
                                }
                                if cmd_path.exists() {
                                    if std::env::var("IPCRAWLER_DEBUG").is_ok() {
                                        eprintln!(
                                            "DEBUG: Found {} at {}",
                                            command,
                                            cmd_path.display()
                                        );
                                    }
                                    return true;
                                }
                            }
                        }
                    }
                }
            }
        }

        // Check each path
        for path in &search_paths {
            if std::path::Path::new(&format!("{}/{}", path, command)).exists() {
                return true;
            }
        }
    }

    false
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
