use colored::*;
use std::process::Command;
use std::collections::HashMap;
use std::path::PathBuf;
use which::which;

pub struct DependencyChecker {
    tool_installations: HashMap<String, ToolInstallation>,
}

#[derive(Debug)]
pub struct ToolInstallation {
    pub name: String,
    pub check_command: String,
    pub version_flag: String,
    pub install_instructions: Vec<InstallMethod>,
    pub required: bool,
}

#[derive(Debug, Clone)]
pub struct InstallMethod {
    pub platform: String,
    pub method: String,
    pub command: String,
}

#[derive(Debug)]
pub struct ToolStatus {
    pub name: String,
    pub installed: bool,
    pub version: Option<String>,
    pub error: Option<String>,
    pub install_suggestions: Vec<InstallMethod>,
}

impl DependencyChecker {
    pub fn new() -> Self {
        let mut tool_installations = HashMap::new();
        
        // Define common reconnaissance tools
        tool_installations.insert("nmap".to_string(), ToolInstallation {
            name: "nmap".to_string(),
            check_command: "nmap".to_string(),
            version_flag: "--version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "macOS".to_string(),
                    method: "Homebrew".to_string(),
                    command: "brew install nmap".to_string(),
                },
                InstallMethod {
                    platform: "Ubuntu/Debian".to_string(),
                    method: "APT".to_string(),
                    command: "sudo apt update && sudo apt install nmap".to_string(),
                },
                InstallMethod {
                    platform: "CentOS/RHEL".to_string(),
                    method: "YUM".to_string(),
                    command: "sudo yum install nmap".to_string(),
                },
                InstallMethod {
                    platform: "Windows".to_string(),
                    method: "Download".to_string(),
                    command: "Download from https://nmap.org/download.html".to_string(),
                },
            ],
            required: true,
        });

        tool_installations.insert("naabu".to_string(), ToolInstallation {
            name: "naabu".to_string(),
            check_command: "naabu".to_string(),
            version_flag: "-version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Go Install".to_string(),
                    command: "go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest".to_string(),
                },
                InstallMethod {
                    platform: "macOS".to_string(),
                    method: "Homebrew".to_string(),
                    command: "brew install naabu".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/projectdiscovery/naabu/releases".to_string(),
                },
            ],
            required: true,
        });

        tool_installations.insert("httpx".to_string(), ToolInstallation {
            name: "httpx".to_string(),
            check_command: "httpx".to_string(),
            version_flag: "-version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Go Install".to_string(),
                    command: "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/projectdiscovery/httpx/releases".to_string(),
                },
            ],
            required: false,
        });

        tool_installations.insert("nuclei".to_string(), ToolInstallation {
            name: "nuclei".to_string(),
            check_command: "nuclei".to_string(),
            version_flag: "-version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Go Install".to_string(),
                    command: "go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest".to_string(),
                },
                InstallMethod {
                    platform: "macOS".to_string(),
                    method: "Homebrew".to_string(),
                    command: "brew install nuclei".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/projectdiscovery/nuclei/releases".to_string(),
                },
            ],
            required: false,
        });

        tool_installations.insert("gobuster".to_string(), ToolInstallation {
            name: "gobuster".to_string(),
            check_command: "gobuster".to_string(),
            version_flag: "version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Go Install".to_string(),
                    command: "go install github.com/OJ/gobuster/v3@latest".to_string(),
                },
                InstallMethod {
                    platform: "Ubuntu/Debian".to_string(),
                    method: "APT".to_string(),
                    command: "sudo apt update && sudo apt install gobuster".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/OJ/gobuster/releases".to_string(),
                },
            ],
            required: false,
        });

        tool_installations.insert("ffuf".to_string(), ToolInstallation {
            name: "ffuf".to_string(),
            check_command: "ffuf".to_string(),
            version_flag: "-V".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Go Install".to_string(),
                    command: "go install github.com/ffuf/ffuf@latest".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/ffuf/ffuf/releases".to_string(),
                },
            ],
            required: false,
        });

        tool_installations.insert("subfinder".to_string(), ToolInstallation {
            name: "subfinder".to_string(),
            check_command: "subfinder".to_string(),
            version_flag: "-version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Go Install".to_string(),
                    command: "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/projectdiscovery/subfinder/releases".to_string(),
                },
            ],
            required: false,
        });

        // Add 'see' markdown renderer as optional enhancement tool
        tool_installations.insert("see".to_string(), ToolInstallation {
            name: "see".to_string(),
            check_command: "see".to_string(),
            version_flag: "--version".to_string(),
            install_instructions: vec![
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Cargo".to_string(),
                    command: "cargo install see-cat".to_string(),
                },
                InstallMethod {
                    platform: "macOS".to_string(),
                    method: "Homebrew".to_string(),
                    command: "brew install guilhermeprokisch/see/see".to_string(),
                },
                InstallMethod {
                    platform: "All Platforms".to_string(),
                    method: "Binary Release".to_string(),
                    command: "Download from https://github.com/guilhermeprokisch/see/releases".to_string(),
                },
            ],
            required: false,
        });

        Self { tool_installations }
    }

    pub fn is_see_available(&self) -> bool {
        matches!(Command::new("see").arg("--version").output(), Ok(output) if output.status.success())
    }

    // 🚫 ANTI-HARDCODING: Generic tool path detection
    pub fn find_tool_path(&self, tool_name: &str) -> Option<PathBuf> {
        which(tool_name).ok()
    }
    
    // 🚫 ANTI-HARDCODING: Generic tool alternative discovery from YAML metadata
    pub fn find_alternative_tool(&self, tool: &crate::config::Tool) -> Option<String> {
        // Get alternatives from tool metadata if available
        if let Some(metadata) = &tool.metadata {
            if let Some(alternatives) = metadata.get("alternatives") {
                if let Some(alt_array) = alternatives.as_array() {
                    for alt in alt_array {
                        if let Some(alt_name) = alt.as_str() {
                            if which(alt_name).is_ok() {
                                return Some(alt_name.to_string());
                            }
                        }
                    }
                }
            }
        }
        None
    }
    
    pub fn get_tool_version(&self, tool_name: &str) -> Option<String> {
        let path = self.find_tool_path(tool_name)?;
        
        // Try common version flags
        for flag in &["--version", "-v", "-V", "version"] {
            if let Ok(output) = Command::new(&path)
                .arg(flag)
                .output()
            {
                if output.status.success() {
                    let version = String::from_utf8_lossy(&output.stdout);
                    if !version.trim().is_empty() {
                        return Some(version.lines().next()?.to_string());
                    }
                }
            }
        }
        None
    }

    pub fn check_tool(&self, tool_name: &str) -> ToolStatus {
        // Extract base tool name (e.g., "nmap_quick" -> "nmap")
        let base_name = self.extract_base_tool_name(tool_name);
        
        if let Some(tool_info) = self.tool_installations.get(&base_name) {
            self.check_tool_installation(tool_info)
        } else {
            // Unknown tool, try basic check
            self.check_unknown_tool(tool_name)
        }
    }

    pub fn check_all_configured_tools(&self, config: &crate::config::Config) -> Vec<ToolStatus> {
        let mut results = Vec::new();
        let mut checked_tools = std::collections::HashSet::new();

        for tool in &config.tools {
            if tool.enabled {
                let base_name = self.extract_base_tool_name(&tool.name);
                if !checked_tools.contains(&base_name) {
                    results.push(self.check_tool(&tool.name));
                    checked_tools.insert(base_name);
                }
            }
        }

        results
    }

    pub fn print_doctor_report(&self, config: &crate::config::Config) {
        println!("{}", "[HEALTH] System Health Check".bright_cyan().bold());
        println!();

        // Check tool dependencies
        let tool_statuses = self.check_all_configured_tools(config);
        
        if tool_statuses.is_empty() {
            println!("{} No tools configured to check", "[WARNING]".yellow());
            return;
        }

        let installed_count = tool_statuses.iter().filter(|t| t.installed).count();
        let total_count = tool_statuses.len();

        println!("{} Tool Dependencies ({}/{}):", 
            "[TOOLS]".bright_blue(), 
            installed_count.to_string().green(), 
            total_count
        );
        println!();

        let mut missing_required = Vec::new();
        let mut missing_optional = Vec::new();

        for status in &tool_statuses {
            let icon = if status.installed { "[INSTALLED]" } else { "[MISSING]" };
            let name_colored = if status.installed { 
                status.name.bright_green() 
            } else { 
                status.name.bright_red() 
            };

            if status.installed {
                if let Some(version) = &status.version {
                    println!("   {} {} ({})", icon, name_colored, version.bright_black());
                } else {
                    println!("   {} {} (version unknown)", icon, name_colored);
                }
            } else {
                println!("   {} {} - {}", icon, name_colored, "Not installed".bright_red());
                
                if let Some(tool_info) = self.tool_installations.get(&status.name) {
                    if tool_info.required {
                        missing_required.push(status);
                    } else {
                        missing_optional.push(status);
                    }
                } else {
                    missing_optional.push(status);
                }
            }
        }

        println!();

        // Show installation instructions for missing tools
        if !missing_required.is_empty() {
            println!("{} Missing Required Tools:", "[REQUIRED]".bright_red());
            self.print_installation_instructions(&missing_required);
            println!();
        }

        if !missing_optional.is_empty() {
            println!("{} Missing Optional Tools:", "[OPTIONAL]".bright_yellow());
            self.print_installation_instructions(&missing_optional);
            println!();
        }

        // Overall health score
        let health_score = (installed_count as f64 / total_count as f64) * 100.0;
        let health_color = match health_score as u8 {
            90..=100 => health_score.to_string().bright_green(),
            70..=89 => health_score.to_string().bright_yellow(),
            _ => health_score.to_string().bright_red(),
        };

        println!("{} System Health Score: {}%", "[SCORE]".bright_blue(), health_color);
        
        if health_score < 100.0 {
            println!("{} Install missing tools to improve reconnaissance capabilities", "[INFO]".bright_blue());
        } else {
            println!("{} All configured tools are available!", "[SUCCESS]".bright_green());
        }
    }

    fn check_tool_installation(&self, tool_info: &ToolInstallation) -> ToolStatus {
        match Command::new(&tool_info.check_command)
            .arg(&tool_info.version_flag)
            .output()
        {
            Ok(output) => {
                if output.status.success() {
                    // Try using the new generic version detection
                    let version = self.get_tool_version(&tool_info.name)
                        .or_else(|| self.extract_version_from_output(&output.stdout, &output.stderr));
                    ToolStatus {
                        name: tool_info.name.clone(),
                        installed: true,
                        version,
                        error: None,
                        install_suggestions: tool_info.install_instructions.clone(),
                    }
                } else {
                    ToolStatus {
                        name: tool_info.name.clone(),
                        installed: false,
                        version: None,
                        error: Some(format!("Command failed with exit code {}", output.status.code().unwrap_or(-1))),
                        install_suggestions: tool_info.install_instructions.clone(),
                    }
                }
            }
            Err(e) => ToolStatus {
                name: tool_info.name.clone(),
                installed: false,
                version: None,
                error: Some(format!("Command not found: {}", e)),
                install_suggestions: tool_info.install_instructions.clone(),
            }
        }
    }

    fn check_unknown_tool(&self, tool_name: &str) -> ToolStatus {
        let base_name = self.extract_base_tool_name(tool_name);
        
        match Command::new(&base_name)
            .arg("--version")
            .output()
            .or_else(|_| Command::new(&base_name).arg("-version").output())
            .or_else(|_| Command::new(&base_name).arg("version").output())
        {
            Ok(output) if output.status.success() => {
                let version = self.extract_version_from_output(&output.stdout, &output.stderr);
                ToolStatus {
                    name: base_name.clone(),
                    installed: true,
                    version,
                    error: None,
                    install_suggestions: vec![
                        InstallMethod {
                            platform: "Manual".to_string(),
                            method: "Search".to_string(),
                            command: format!("Search for '{}' installation instructions online", &base_name),
                        }
                    ],
                }
            }
            _ => ToolStatus {
                name: base_name.clone(),
                installed: false,
                version: None,
                error: Some("Tool not found".to_string()),
                install_suggestions: vec![
                    InstallMethod {
                        platform: "Manual".to_string(),
                        method: "Search".to_string(),
                        command: format!("Search for '{}' installation instructions online", &base_name),
                    }
                ],
            }
        }
    }

    fn extract_base_tool_name(&self, tool_name: &str) -> String {
        // Extract base tool name from variations like "nmap_quick", "nmap-fast", etc.
        tool_name.split('_').next()
            .unwrap_or(tool_name)
            .split('-').next()
            .unwrap_or(tool_name)
            .to_string()
    }

    fn extract_version_from_output(&self, stdout: &[u8], stderr: &[u8]) -> Option<String> {
        let stdout_str = String::from_utf8_lossy(stdout);
        let stderr_str = String::from_utf8_lossy(stderr);
        let combined = format!("{} {}", stdout_str, stderr_str);

        // Try to extract version using common patterns
        let version_patterns = [
            r"version (\d+\.\d+(?:\.\d+)?)",
            r"v(\d+\.\d+(?:\.\d+)?)",
            r"(\d+\.\d+(?:\.\d+)?)",
        ];

        for pattern in &version_patterns {
            if let Ok(regex) = regex::Regex::new(pattern) {
                if let Some(captures) = regex.captures(&combined) {
                    if let Some(version) = captures.get(1) {
                        return Some(version.as_str().to_string());
                    }
                }
            }
        }

        // Fallback: return first line of output if it looks like version info
        let first_line = combined.lines().next()?.trim();
        if first_line.len() < 100 && (first_line.contains("version") || first_line.contains("v")) {
            Some(first_line.to_string())
        } else {
            None
        }
    }

    fn print_installation_instructions(&self, statuses: &[&ToolStatus]) {
        for status in statuses {
            println!("   {} {}:", "[TOOL]".bright_blue(), status.name.bright_white());
            
            // Show error information if available
            if let Some(ref error) = status.error {
                println!("      {} {}", "[ERROR]".bright_red(), error.bright_black());
            }
            
            let current_os = std::env::consts::OS;
            let mut shown_methods = std::collections::HashSet::new();
            
            // Show OS-specific instructions first
            for method in &status.install_suggestions {
                if method.platform.to_lowercase().contains(current_os) || 
                   (current_os == "macos" && method.platform.contains("macOS")) {
                    println!("      {} {}: {}", 
                        "[PREFERRED]".bright_green(),
                        method.method.bright_cyan(), 
                        method.command.bright_black()
                    );
                    shown_methods.insert(&method.method);
                }
            }
            
            // Show cross-platform methods
            for method in &status.install_suggestions {
                if method.platform.contains("All Platforms") && !shown_methods.contains(&method.method) {
                    println!("      {} {}: {}", 
                        "[GENERAL]".bright_blue(),
                        method.method.bright_cyan(), 
                        method.command.bright_black()
                    );
                    shown_methods.insert(&method.method);
                }
            }
            
            println!();
        }
    }
}