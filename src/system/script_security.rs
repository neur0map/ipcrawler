use anyhow::{Context, Result};
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::Path;

/// Security validator for shell scripts
pub struct ScriptSecurity;

impl ScriptSecurity {
    /// Dangerous commands that should be blocked in scripts
    /// Only truly destructive operations are included
    const DANGEROUS_COMMANDS: &'static [&'static str] = &[
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=/dev/zero of=/dev/sd",   // Disk wiping
        "dd if=/dev/zero of=/dev/nvme", // Disk wiping
        ":(){ :|:& };:",                // Fork bomb
        "/dev/sda",                     // Direct disk access
        "/dev/nvme",                    // Direct disk access (block device)
        "format c:",                    // Disk formatting (Windows style)
        "systemctl poweroff",
        "systemctl reboot",
        "userdel root", // Only block deletion of root user
        "passwd root",  // Only block root password changes
        "chmod 777 /",  // Only block dangerous root permissions
        "chown root /", // Only block dangerous root ownership changes
    ];

    /// Suspicious patterns that warrant warnings
    /// Note: Reduced to avoid false positives in legitimate recon scripts
    const SUSPICIOUS_PATTERNS: &'static [&'static str] = &[
        "base64 -d | bash",               // Decode and execute (truly suspicious)
        "base64 -d | sh",                 // Decode and execute (truly suspicious)
        "xxd -r | bash",                  // Reverse hex and execute
        "nc -l",                          // Netcat listener (reverse shell)
        "ncat -l",                        // Ncat listener (reverse shell)
        "python -c 'import os;os.system", // Arbitrary OS commands
        "curl http://",                   // Only flag if downloading (removed overly broad pattern)
        "wget http://",                   // Only flag if downloading (removed overly broad pattern)
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

        // Check for dangerous commands with improved patterns
        for dangerous in Self::DANGEROUS_COMMANDS {
            let pattern = if dangerous.contains(' ') {
                // For multi-word commands, use more flexible matching
                format!(r"{}([^\w]|$)", regex::escape(dangerous))
            } else {
                // For single words, check word boundaries
                format!(r"\b{}\b", regex::escape(dangerous))
            };

            if let Ok(re) = regex::Regex::new(&pattern) {
                if re.is_match(&content) {
                    result.is_safe = false;
                    result.dangerous_commands.push(dangerous.to_string());
                }
            } else {
                // Fallback to simple contains if regex fails
                if content.contains(dangerous) {
                    result.is_safe = false;
                    result.dangerous_commands.push(dangerous.to_string());
                }
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
    /// Print minimal report - only for truly dangerous content
    pub fn print_report(&self) {
        if !self.is_safe {
            eprintln!(
                "⚠ Script validation failed: {}",
                self.dangerous_commands.join(", ")
            );
        }
    }

    /// Get a concise summary for logging
    pub fn summary(&self) -> String {
        if !self.is_safe {
            format!("BLOCKED: {}", self.dangerous_commands.join(", "))
        } else if !self.suspicious_patterns.is_empty() {
            format!("Warning: {}", self.suspicious_patterns.join(", "))
        } else {
            "OK".to_string()
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
