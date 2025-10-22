use anyhow::{Context, Result};
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::Path;

/// Security validator for shell scripts
pub struct ScriptSecurity;

impl ScriptSecurity {
    /// Dangerous commands that should be blocked in scripts
    const DANGEROUS_COMMANDS: &'static [&'static str] = &[
        "rm -rf /",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:", // Fork bomb
        "wget http",     // Downloading executables
        "curl http",     // Downloading from internet
        "/dev/sda",      // Direct disk access
        "/dev/nvme",     // Direct disk access
        "format",        // Disk formatting
        "shutdown",      // System shutdown
        "reboot",        // System reboot
        "init 0",        // Shutdown
        "init 6",        // Reboot
        "systemctl poweroff",
        "systemctl reboot",
        "userdel",    // Delete users
        "passwd",     // Change passwords
        "chmod 777",  // Dangerous permissions
        "chown root", // Change ownership to root
        "su -",       // Switch user
        "sudo su",    // Escalate to root
        "eval",       // Arbitrary code execution
        "exec",       // Execute arbitrary commands
    ];

    /// Suspicious patterns that warrant warnings
    const SUSPICIOUS_PATTERNS: &'static [&'static str] = &[
        "base64 -d", // Decode base64 (often used to hide commands)
        "xxd -r",    // Reverse hex dump
        "/dev/tcp/", // Network connections
        "/dev/udp/", // Network connections
        "nc -l",     // Netcat listener
        "ncat -l",   // Ncat listener
        "socat",     // Socket cat (can be used maliciously)
        "python -c", // Execute Python code
        "perl -e",   // Execute Perl code
        "ruby -e",   // Execute Ruby code
        "php -r",    // Execute PHP code
        "bash -c",   // Execute bash code
        "sh -c",     // Execute sh code
    ];

    /// Validates a script for dangerous commands before execution
    pub fn validate_script<P: AsRef<Path>>(script_path: P) -> Result<ValidationResult> {
        let path = script_path.as_ref();
        let content = fs::read_to_string(path)
            .with_context(|| format!("Failed to read script: {}", path.display()))?;

        let mut result = ValidationResult {
            is_safe: true,
            dangerous_commands: Vec::new(),
            suspicious_patterns: Vec::new(),
            warnings: Vec::new(),
        };

        // Check for dangerous commands
        for dangerous in Self::DANGEROUS_COMMANDS {
            if content.contains(dangerous) {
                result.is_safe = false;
                result.dangerous_commands.push(dangerous.to_string());
            }
        }

        // Check for suspicious patterns
        for suspicious in Self::SUSPICIOUS_PATTERNS {
            if content.contains(suspicious) {
                result.suspicious_patterns.push(suspicious.to_string());
                result.warnings.push(format!(
                    "Suspicious pattern detected: {}. Please review the script manually.",
                    suspicious
                ));
            }
        }

        // Check for shebang
        if !content.starts_with("#!/bin/bash") && !content.starts_with("#!/bin/sh") {
            result
                .warnings
                .push("Script missing proper shebang (#!/bin/bash or #!/bin/sh)".to_string());
        }

        // Check file size (prevent extremely large scripts)
        let metadata = fs::metadata(path)?;
        if metadata.len() > 1_048_576 {
            // 1MB limit
            result.is_safe = false;
            result
                .dangerous_commands
                .push("Script exceeds 1MB size limit".to_string());
        }

        Ok(result)
    }

    /// Makes a script executable (chmod +x)
    pub fn make_executable<P: AsRef<Path>>(script_path: P) -> Result<()> {
        let path = script_path.as_ref();
        let metadata = fs::metadata(path)
            .with_context(|| format!("Failed to get metadata for: {}", path.display()))?;

        let mut permissions = metadata.permissions();

        // Add execute permissions for owner
        #[cfg(unix)]
        {
            let mode = permissions.mode();
            permissions.set_mode(mode | 0o100); // Add execute for owner
        }

        fs::set_permissions(path, permissions)
            .with_context(|| format!("Failed to set permissions for: {}", path.display()))?;

        Ok(())
    }
}

#[derive(Debug)]
pub struct ValidationResult {
    pub is_safe: bool,
    pub dangerous_commands: Vec<String>,
    pub suspicious_patterns: Vec<String>,
    pub warnings: Vec<String>,
}

impl ValidationResult {
    pub fn print_report(&self) {
        if !self.is_safe {
            eprintln!("SECURITY WARNING: Script contains dangerous commands!");
            for cmd in &self.dangerous_commands {
                eprintln!("  - {}", cmd);
            }
        }

        if !self.suspicious_patterns.is_empty() {
            eprintln!("WARNING: Script contains suspicious patterns:");
            for pattern in &self.suspicious_patterns {
                eprintln!("  - {}", pattern);
            }
        }

        if !self.warnings.is_empty() {
            for warning in &self.warnings {
                eprintln!("  {}", warning);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_dangerous_script_detection() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "#!/bin/bash").unwrap();
        writeln!(file, "rm -rf /").unwrap();

        let result = ScriptSecurity::validate_script(file.path()).unwrap();
        assert!(!result.is_safe);
        assert!(!result.dangerous_commands.is_empty());
    }

    #[test]
    fn test_safe_script() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "#!/bin/bash").unwrap();
        writeln!(file, "echo 'Hello World'").unwrap();
        writeln!(file, "nmap -sV 192.168.1.1").unwrap();

        let result = ScriptSecurity::validate_script(file.path()).unwrap();
        assert!(result.is_safe);
        assert!(result.dangerous_commands.is_empty());
    }
}
