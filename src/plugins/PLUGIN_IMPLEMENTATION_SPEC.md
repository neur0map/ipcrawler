# ipcrawler Plugin Implementation Specification v1.0
# Machine-readable plugin development guide for AI coders

## REQUIRED_IMPORTS
```rust
use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::{Service, Proto}, state::RunState};
use crate::config::GlobalConfig;
use crate::executors::command::execute;
use chrono::Utc;
```

## PLUGIN_TYPE_DEFINITIONS

### PORT_SCANNER_PLUGIN
```rust
#[derive(Clone)]
pub struct {PLUGIN_NAME};

#[async_trait]
impl crate::plugins::types::PortScan for {PLUGIN_NAME} {
    fn name(&self) -> &'static str { "{plugin_name_lowercase}" }
    
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        // REQUIRED: Get target and directories
        let target = &state.target;
        let dirs = state.dirs.as_ref().unwrap();
        
        // REQUIRED: Get tool config from global.toml
        let tool_config = &config.tools.{plugin_name_lowercase};
        let mut args = tool_config.base_args.clone();
        
        // REQUIRED: Add tool-specific arguments based on config
        // [ADD_TOOL_SPECIFIC_CONFIG_LOGIC_HERE]
        
        args.push(target.to_string());
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        // REQUIRED: Execute command with timeout
        let command = &tool_config.command;
        let timeout = Some(tool_config.limits.timeout_ms);
        let result = execute(command, &args_str, &dirs.scans, timeout).await?;
        
        // REQUIRED: Parse output into Service objects
        let services = self.parse_output(&result.stdout, target)?;
        
        // REQUIRED: Write plugin results
        self.write_plugin_results(&services, &dirs.scans)?;
        
        Ok(services)
    }
}

impl {PLUGIN_NAME} {
    // REQUIRED: Result writing method
    fn write_plugin_results(&self, results: &[Service], scans_dir: &std::path::Path) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== {} Results ===\n", self.name()));
        content.push_str(&format!("Found {} services:\n\n", results.len()));
        
        for service in results {
            content.push_str(&format!(
                "{}:{} {} ({:?}){}\n",
                service.address, 
                service.port, 
                service.name, 
                service.proto,
                if service.secure { " [SSL/TLS]" } else { "" }
            ));
        }
        
        content.push_str(&format!("\nTimestamp: {}\n", Utc::now()));
        let result_file = scans_dir.join(format!("{}_results.txt", self.name()));
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        Ok(())
    }
    
    // REQUIRED: Output parsing method
    fn parse_output(&self, output: &str, target: &str) -> Result<Vec<Service>> {
        let mut services = Vec::new();
        // [ADD_OUTPUT_PARSING_LOGIC_HERE]
        // MUST return Vec<Service> with:
        // - service.address = target.to_string()
        // - service.port = detected_port
        // - service.name = service_name.to_string()
        // - service.proto = Proto::Tcp or Proto::Udp
        // - service.secure = true/false based on detection
        
        // Example parsing pattern:
        for line in output.lines() {
            if line.contains("open") {
                // Parse port and service from line
                let service = Service {
                    address: target.to_string(),
                    port: 80, // Parse from output
                    name: "http".to_string(), // Parse from output
                    proto: Proto::Tcp,
                    secure: false, // Detect SSL/TLS
                };
                services.push(service);
            }
        }
        
        Ok(services)
    }
}
```

### SERVICE_SCANNER_PLUGIN
```rust
#[derive(Clone)]
pub struct {PLUGIN_NAME};

#[async_trait]
impl crate::plugins::types::ServiceScan for {PLUGIN_NAME} {
    fn name(&self) -> &'static str { "{plugin_name_lowercase}" }
    
    fn matches(&self, service: &Service) -> bool {
        // REQUIRED: Define service matching logic
        // Examples:
        // service.name.contains("ssh") || service.port == 22
        // service.name.contains("ftp") || service.port == 21
        // service.port >= 8000 && service.port <= 9000
        // service.name.contains("http") && service.port != 80
        false // Replace with actual matching logic
    }
    
    async fn run(&self, service: &Service, state: &RunState, config: &GlobalConfig) -> Result<()> {
        let dirs = state.dirs.as_ref().unwrap();
        
        // REQUIRED: Get tool config
        let tool_config = &config.tools.{plugin_name_lowercase};
        let mut args = tool_config.base_args.clone();
        
        // REQUIRED: Add service-specific arguments
        args.push(format!("{}:{}", service.address, service.port));
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        // REQUIRED: Execute command
        let command = &tool_config.command;
        let timeout = Some(tool_config.limits.timeout_ms);
        let result = execute(command, &args_str, &dirs.scans, timeout).await;
        
        // REQUIRED: Determine success/failure
        let success = result.is_ok();
        
        // REQUIRED: Write plugin results
        self.write_plugin_results(service, success, &result, &dirs.scans)?;
        
        Ok(())
    }
}

impl {PLUGIN_NAME} {
    // REQUIRED: Result writing method
    fn write_plugin_results(&self, service: &Service, success: bool, result: &Result<crate::executors::command::CommandResult>, scans_dir: &std::path::Path) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== {} Results ===\n", self.name()));
        content.push_str(&format!("Target: {}:{}\n", service.address, service.port));
        content.push_str(&format!("Status: {}\n", if success { "SUCCESS" } else { "FAILED" }));
        content.push_str(&format!("Service: {} ({:?})\n", service.name, service.proto));
        content.push_str(&format!("Secure: {}\n", service.secure));
        
        if let Ok(cmd_result) = result {
            if !cmd_result.stdout.is_empty() {
                content.push_str(&format!("Output:\n{}\n", cmd_result.stdout));
            }
            if !cmd_result.stderr.is_empty() {
                content.push_str(&format!("Errors:\n{}\n", cmd_result.stderr));
            }
        }
        
        content.push_str(&format!("Timestamp: {}\n", Utc::now()));
        let result_file = scans_dir.join(format!("{}_{}_{}_{}_results.txt", 
            self.name(), service.address, service.port, service.name));
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        Ok(())
    }
}
```

## CONFIGURATION_INTEGRATION

### GLOBAL_TOML_SECTION
```toml
[tools.{plugin_name_lowercase}]
command = "{default_command}"
base_args = ["{default}", "{args}"]

[tools.{plugin_name_lowercase}.limits]
timeout_ms = {default_timeout}
max_retries = {default_retries}

[tools.{plugin_name_lowercase}.options]
# Tool-specific options here
option1 = {default_value}
option2 = {default_value}
```

### CONFIG_STRUCT_DEFINITION
Add to src/config/types.rs in ToolsConfig struct:
```rust
pub {plugin_name_lowercase}: {PluginName}Config,
```

Add new config struct:
```rust
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Config {
    pub command: String,
    pub base_args: Vec<String>,
    pub options: {PluginName}Options,
    pub limits: {PluginName}Limits,
}

impl Default for {PluginName}Config {
    fn default() -> Self {
        Self {
            command: "{default_command}".to_string(),
            base_args: vec!["{default}".to_string(), "{args}".to_string()],
            options: {PluginName}Options::default(),
            limits: {PluginName}Limits::default(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Options {
    // Tool-specific options
    pub example_option: bool,
}

impl Default for {PluginName}Options {
    fn default() -> Self {
        Self {
            example_option: true,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Limits {
    pub timeout_ms: u64,
    pub max_retries: u32,
}

impl Default for {PluginName}Limits {
    fn default() -> Self {
        Self {
            timeout_ms: 30000, // 30 seconds
            max_retries: 1,
        }
    }
}
```

Update ToolsConfig Default implementation:
```rust
impl Default for ToolsConfig {
    fn default() -> Self {
        Self {
            nmap: NmapConfig::default(),
            http_probe: HttpProbeConfig::default(),
            {plugin_name_lowercase}: {PluginName}Config::default(), // ADD THIS
            custom_tools: HashMap::new(),
        }
    }
}
```

## PLUGIN_REGISTRY_INTEGRATION

### ADD_TO_SCHEDULER_REGISTRY
In src/core/scheduler.rs PluginRegistry::default():

For port scanners:
```rust
port_scans: vec![
    Box::new(crate::plugins::portscan_nmap::NmapPortScan),
    Box::new(crate::plugins::{plugin_module}::{PluginName}), // ADD THIS
],
```

For service scanners:
```rust
service_scans: vec![
    Box::new(crate::plugins::http_probe::HttpProbe),
    Box::new(crate::plugins::{plugin_module}::{PluginName}), // ADD THIS
],
```

## REQUIRED_FILE_STRUCTURE
```
src/plugins/{plugin_name_lowercase}.rs  // Main plugin file
src/plugins/mod.rs                      // Add pub mod {plugin_name_lowercase};
```

### MODULE_DECLARATION
Add to src/plugins/mod.rs:
```rust
pub mod {plugin_name_lowercase};
```

## TESTING_REQUIREMENTS
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::models::{Service, Proto};
    
    #[test]
    fn test_service_matching() {
        let plugin = {PluginName};
        let service = Service {
            address: "127.0.0.1".to_string(),
            port: 80,
            name: "http".to_string(),
            proto: Proto::Tcp,
            secure: false,
        };
        assert!(plugin.matches(&service));
    }
    
    #[test]
    fn test_output_parsing() {
        let plugin = {PluginName};
        let test_output = "{sample_tool_output}";
        let result = plugin.parse_output(test_output, "127.0.0.1");
        assert!(result.is_ok());
        let services = result.unwrap();
        assert!(!services.is_empty());
    }
    
    #[test]
    fn test_plugin_name() {
        let plugin = {PluginName};
        assert_eq!(plugin.name(), "{plugin_name_lowercase}");
    }
    
    #[test]
    fn test_clone_implementation() {
        let plugin = {PluginName};
        let cloned = plugin.clone();
        assert_eq!(plugin.name(), cloned.name());
    }
}
```

## IMPLEMENTATION_CHECKLIST
- [ ] Define plugin struct with #[derive(Clone)]
- [ ] Implement required trait (PortScan or ServiceScan)
- [ ] Add name() method returning &'static str
- [ ] Implement matches() for ServiceScan plugins
- [ ] Add run() method with proper async signature
- [ ] Implement write_plugin_results() method
- [ ] Add parse_output() method for PortScan plugins (required)
- [ ] Create configuration structs in config/types.rs
- [ ] Add plugin config to ToolsConfig struct
- [ ] Update ToolsConfig Default implementation
- [ ] Add plugin to PluginRegistry::default() in scheduler.rs
- [ ] Add module declaration to plugins/mod.rs
- [ ] Write unit tests for all public methods
- [ ] Test integration with scheduler
- [ ] Verify configuration loading works
- [ ] Test parallel execution compatibility

## ERROR_HANDLING_PATTERNS
```rust
// Use anyhow::Result for all return types
// Handle expected failures gracefully with appropriate log levels
// Always write result files even on failure
// Use ? operator for propagating critical errors
// Handle timeouts and process cleanup properly
// Log at debug level for expected failures, warn for unexpected
```

## PARALLEL_EXECUTION_COMPATIBILITY
```rust
// All plugins MUST implement Clone for parallel execution
// Use Arc<Self> internally if needed for shared state
// Ensure all fields are thread-safe (Send + Sync)
// Avoid mutable shared state between plugin instances
// Use atomic operations or mutexes for shared counters
```

## SERVICE_OBJECT_SPECIFICATION
```rust
pub struct Service {
    pub address: String,    // Target IP/hostname
    pub port: u16,         // Port number
    pub name: String,      // Service name (http, ssh, ftp, etc.)
    pub proto: Proto,      // Proto::Tcp or Proto::Udp
    pub secure: bool,      // true for SSL/TLS services
}

// Proto enum values:
// Proto::Tcp - for TCP services
// Proto::Udp - for UDP services
```

## COMMON_PATTERNS

### Port Scanner Example (masscan):
```rust
// Parse masscan output: "Discovered open port 80/tcp on 192.168.1.1"
if line.contains("Discovered open port") {
    let parts: Vec<&str> = line.split_whitespace().collect();
    if parts.len() >= 6 {
        let port_proto = parts[3]; // "80/tcp"
        let address = parts[5];    // "192.168.1.1"
        if let Some(slash_pos) = port_proto.find('/') {
            let port = port_proto[..slash_pos].parse::<u16>()?;
            let proto = if port_proto.ends_with("tcp") { Proto::Tcp } else { Proto::Udp };
            // Create Service object...
        }
    }
}
```

### Service Scanner Example (ssh):
```rust
fn matches(&self, service: &Service) -> bool {
    service.name.contains("ssh") || 
    service.port == 22 || 
    (service.port >= 2200 && service.port <= 2299)
}
```

This specification provides complete implementation patterns for any AI coder to follow when adding new plugins to the ipcrawler system, ensuring compatibility with parallel execution, configuration system, and monitoring integration.