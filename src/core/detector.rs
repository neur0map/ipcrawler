use anyhow::Result;
use std::process::Command;
use regex::Regex;

#[derive(Debug, Clone)]
pub struct SystemInfo {
    pub os: OS,
    pub arch: String,
    pub has_sudo: bool,
    pub shell: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum OS {
    Linux,
    Windows,
    MacOS,
}

#[derive(Debug, Clone)]
pub struct ToolInfo {
    pub name: String,
    pub version: Option<String>,
    pub is_available: bool,
}

#[derive(Clone)]
pub struct SystemDetector {
    system_info: SystemInfo,
    tools: Vec<ToolInfo>,
}

impl SystemDetector {
    pub fn new() -> Result<Self> {
        let system_info = Self::detect_system_info()?;
        let tools = Self::detect_tools(&system_info)?;
        
        Ok(Self {
            system_info,
            tools,
        })
    }

    fn detect_system_info() -> Result<SystemInfo> {
        let os = Self::detect_os();
        let arch = Self::detect_arch();
        let has_sudo = Self::detect_sudo_access(&os);
        let shell = Self::detect_shell();

        Ok(SystemInfo {
            os,
            arch,
            has_sudo,
            shell,
        })
    }

    fn detect_os() -> OS {
        #[cfg(target_os = "linux")]
        return OS::Linux;
        
        #[cfg(target_os = "windows")]
        return OS::Windows;
        
        #[cfg(target_os = "macos")]
        return OS::MacOS;
        
        #[cfg(not(any(target_os = "linux", target_os = "windows", target_os = "macos")))]
        {
            // Fallback detection at runtime
            if cfg!(target_os = "linux") {
                OS::Linux
            } else if cfg!(target_os = "windows") {
                OS::Windows
            } else if cfg!(target_os = "macos") {
                OS::MacOS
            } else {
                OS::Unknown
            }
        }
    }

    fn detect_arch() -> String {
        std::env::consts::ARCH.to_string()
    }

    fn detect_sudo_access(os: &OS) -> bool {
        match os {
            OS::Linux | OS::MacOS => {
                // Try to run a simple command with sudo -n (non-interactive)
                Command::new("sudo")
                    .arg("-n")
                    .arg("true")
                    .output()
                    .map(|output| output.status.success())
                    .unwrap_or(false)
            }
            OS::Windows => {
                // On Windows, check if running as administrator
                Command::new("net")
                    .arg("session")
                    .output()
                    .map(|output| output.status.success())
                    .unwrap_or(false)
            }
            OS::Unknown => false,
        }
    }

    fn detect_shell() -> String {
        std::env::var("SHELL").unwrap_or_else(|_| {
            if cfg!(target_os = "windows") {
                std::env::var("COMSPEC").unwrap_or_else(|_| "cmd.exe".to_string())
            } else {
                "/bin/sh".to_string()
            }
        })
    }

    fn detect_tools(system_info: &SystemInfo) -> Result<Vec<ToolInfo>> {
        let mut tools = Vec::new();
        
        // Network scanning tools
        tools.push(Self::check_tool("nmap", &["-version"], system_info));
        tools.push(Self::check_tool("rustscan", &["--version"], system_info));
        tools.push(Self::check_tool("masscan", &["--version"], system_info));
        
        // DNS and discovery tools
        tools.push(Self::check_tool("dig", &[], system_info));
        tools.push(Self::check_tool("nslookup", &[], system_info));
        tools.push(Self::check_tool("whois", &[], system_info));
        tools.push(Self::check_tool("host", &[], system_info));
        
        // Connectivity tools
        tools.push(Self::check_tool("ping", &[], system_info));
        tools.push(Self::check_tool("ping6", &[], system_info));
        tools.push(Self::check_tool("traceroute", &[], system_info));
        tools.push(Self::check_tool("tracert", &[], system_info));
        
        // SSL/TLS tools
        tools.push(Self::check_tool("openssl", &["version"], system_info));
        tools.push(Self::check_tool("sslscan", &[], system_info));
        
        // Web tools
        tools.push(Self::check_tool("curl", &["--version"], system_info));
        tools.push(Self::check_tool("wget", &["--version"], system_info));
        tools.push(Self::check_tool("httpie", &["--version"], system_info));
        
        // Information gathering
        tools.push(Self::check_tool("what", &[], system_info));
        tools.push(Self::check_tool("wafw00f", &[], system_info));
        tools.push(Self::check_tool("nikto", &[], system_info));
        
        // Windows-specific tools
        if system_info.os == OS::Windows {
            tools.push(Self::check_tool("powershell", &["-Command", "Get-Host"], system_info));
            tools.push(Self::check_tool("cmd", &[], system_info));
        }
        
        Ok(tools)
    }

    fn check_tool(name: &str, version_args: &[&str], system_info: &SystemInfo) -> ToolInfo {
        let path = Self::which(name);
        let is_available = path.is_some();
        
        let version = if is_available {
            Self::get_tool_version(name, version_args)
        } else {
            None
        };

        let requires_sudo = Self::tool_requires_sudo(name, system_info);

        ToolInfo {
            name: name.to_string(),
            version,
            path,
            is_available,
            requires_sudo,
        }
    }

    fn which(tool: &str) -> Option<String> {
        #[cfg(target_os = "windows")]
        {
            // On Windows, also check for .exe extension
            if let Ok(output) = Command::new("where").arg(tool).output() {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout);
                    return Some(path.lines().next()?.to_string());
                }
            }
            
            if let Ok(output) = Command::new("where").arg(&format!("{}.exe", tool)).output() {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout);
                    return Some(path.lines().next()?.to_string());
                }
            }
        }
        
        #[cfg(not(target_os = "windows"))]
        {
            if let Ok(output) = Command::new("which").arg(tool).output() {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout);
                    return Some(path.trim().to_string());
                }
            }
        }
        
        None
    }

    fn get_tool_version(tool: &str, args: &[&str]) -> Option<String> {
        let mut cmd = Command::new(tool);
        for arg in args {
            cmd.arg(arg);
        }
        
        if let Ok(output) = cmd.output() {
            if output.status.success() {
                let version_output = String::from_utf8_lossy(&output.stdout);
                let version_error = String::from_utf8_lossy(&output.stderr);
                let combined = format!("{} {}", version_output, version_error);
                
                // Try to extract version number
                Self::extract_version(&combined)
            } else {
                // Some tools return version on stderr even with success=false
                let version_error = String::from_utf8_lossy(&output.stderr);
                Self::extract_version(&version_error)
            }
        } else {
            None
        }
    }

    fn extract_version(output: &str) -> Option<String> {
        // Common version patterns
        let patterns = [
            r"v?(\d+\.\d+\.\d+)",
            r"version\s+(\d+\.\d+\.\d+)",
            r"(\d+\.\d+\.\d+)",
            r"v?(\d+\.\d+)",
            r"version\s+(\d+\.\d+)",
            r"(\d+\.\d+)",
        ];
        
        for pattern in &patterns {
            if let Ok(re) = Regex::new(pattern) {
                if let Some(captures) = re.captures(output) {
                    if let Some(version) = captures.get(1) {
                        return Some(version.as_str().to_string());
                    }
                }
            }
        }
        
        None
    }

    fn tool_requires_sudo(tool: &str, system_info: &SystemInfo) -> bool {
        match tool {
            "nmap" => {
                // Nmap requires sudo for certain scan types (SYN scan, OS detection, etc.)
                !system_info.has_sudo
            }
            "masscan" => true, // Usually requires root privileges
            "ping" => {
                // On many systems, ping requires root
                system_info.os == OS::Linux && !system_info.has_sudo
            }
            "traceroute" => {
                // Some traceroute implementations require root
                system_info.os == OS::Linux && !system_info.has_sudo
            }
            "nikto" => false, // Usually doesn't require root
            "sslscan" => false, // Usually doesn't require root
            _ => false,
        }
    }

    pub fn get_system_info(&self) -> &SystemInfo {
        &self.system_info
    }

    pub fn is_tool_available(&self, name: &str) -> bool {
        self.tools.iter().any(|tool| tool.name == name && tool.is_available)
    }

    pub fn get_tool_recommendations(&self) -> Vec<String> {
        let mut recommendations = vec![];
        
        // Essential tools for reconnaissance
        let essential = ["nmap", "dig", "ping", "curl"];
        for tool in &essential {
            if !self.is_tool_available(tool) {
                recommendations.push(format!("Install {} for basic reconnaissance", tool));
            }
        }
        
        // Advanced tools
        let advanced = ["masscan", "sslscan", "nikto"];
        for tool in &advanced {
            if !self.is_tool_available(tool) {
                recommendations.push(format!("Install {} for advanced scanning", tool));
            }
        }
        
        recommendations
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_detection() {
        let detector = SystemDetector::new().unwrap();
        
        // Should detect some OS
        assert!(detector.system_info.os != OS::Unknown);
        
        // Should detect some tools
        assert!(!detector.tools.is_empty());
    }

    #[test]
    fn test_tool_availability() {
        let detector = SystemDetector::new().unwrap();
        
        // Check if common tools are detected
        let has_ping = detector.is_tool_available("ping");
        let has_nmap = detector.is_tool_available("nmap");
        
        // At least one should be available on most systems
        assert!(has_ping || has_nmap);
    }
}