# ipcrawler Plugin Implementation Specification v2.0
# Machine-readable plugin development guide for AI coders

## ARCHITECTURE_OVERVIEW

The ipcrawler system supports **reconnaissance plugins** that implement the `PortScan` trait. All plugins run concurrently, provide real-time UI feedback, and create persistent scan results.

**Current Plugin Types:**
- **DNS Reconnaissance** - Query DNS records and resolve hostnames
- **Network Discovery** - Identify open ports and services
- **Service Enumeration** - Probe specific services for details

## PLUGIN_DEVELOPMENT_PROCESS

### STEP_1_ANALYSIS_PHASE
Before coding, analyze your target tool:

1. **Command Structure**: How does the tool accept arguments?
2. **Output Format**: What does the tool's output look like?
3. **Error Conditions**: How does the tool indicate failures?
4. **Record Types**: What types of information does it discover?
5. **Target Support**: Does it handle IPs, domains, or both?

### STEP_2_DESIGN_DECISIONS
Make these architectural choices:

1. **Plugin Name**: Choose a clear, lowercase identifier
2. **Protocol**: Will it discover TCP or UDP services?
3. **Record Types**: What information categories will it report?
4. **Query Strategy**: Single query vs multiple queries per target?
5. **Error Tolerance**: Continue on partial failures or stop completely?

### STEP_3_IMPLEMENTATION_STRUCTURE
Every plugin follows this pattern:

```rust
#[derive(Clone)]
pub struct YourPlugin;

impl YourPlugin {
    // Core validation logic
    fn validate_target(&self, target: &str) -> bool { /* */ }
    
    // UI communication
    fn send_log(&self, ui_sender: &UiSender, level: &str, message: &str) { /* */ }
    
    // Tool execution
    async fn execute_tool(&self, target: &str, query_type: &str, ui_sender: &UiSender) -> Result<String> { /* */ }
    
    // Output processing
    fn parse_output(&self, output: &str, query_type: &str, target: &str) -> Vec<String> { /* */ }
    
    // File persistence
    fn write_results(&self, results: &[(String, Vec<String>)], scans_dir: &Path, target: &str) -> Result<()> { /* */ }
    
    // Tool-specific configuration
    fn get_command_name(&self) -> &str { /* */ }
    fn build_arguments(&self, target: &str, query_type: &str) -> Vec<String> { /* */ }
    fn get_supported_query_types(&self) -> Vec<&str> { /* */ }
    fn get_protocol(&self) -> Proto { /* */ }
    fn get_query_delay(&self) -> u64 { /* */ }
}

#[async_trait]
impl PortScan for YourPlugin {
    fn name(&self) -> &'static str { "your_plugin" }
    
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        // Main execution logic
    }
}
```

## REQUIRED_IMPORTS
```rust
use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::{Service, Proto}, state::RunState};
use crate::plugins::types::PortScan;
use crate::config::GlobalConfig;
use crate::executors::command::execute;
use crate::ui::events::UiEvent;
use tokio::sync::mpsc;
use chrono::Utc;
```

## PLUGIN_TEMPLATE

### BASIC_STRUCTURE
```rust
#[derive(Clone)]
pub struct {PluginName}Plugin;

impl {PluginName}Plugin {
    /// Validate if target is acceptable for this tool
    fn validate_target(&self, target: &str) -> bool {
        // IMPLEMENT: Tool-specific validation logic
        // Common patterns:
        // - IP address validation: target.parse::<std::net::IpAddr>().is_ok()
        // - Domain validation: target.contains('.') && !target.contains(' ')
        // - URL validation: target.starts_with("http")
        // - Port validation: target.parse::<u16>().is_ok()
        true
    }

    /// Send structured log message to UI
    fn send_log(&self, ui_sender: &mpsc::UnboundedSender<UiEvent>, level: &str, message: &str) {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: level.to_string(),
            message: message.to_string(),
        });
    }

    /// Execute the external tool and capture output
    async fn execute_tool(&self, target: &str, query_type: &str, ui_sender: &mpsc::UnboundedSender<UiEvent>) -> Result<String> {
        self.send_log(ui_sender, "INFO", &format!("Running {} {} query for {}", self.name(), query_type, target));
        
        // Build command arguments
        let args = self.build_arguments(target, query_type);
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        let timeout = Some(10000); // 10 second timeout
        
        // Execute command
        match execute(self.get_command_name(), &args_str, std::path::Path::new("."), timeout).await {
            Ok(command_result) => {
                if command_result.exit_code == 0 {
                    self.send_log(ui_sender, "INFO", &format!("{} {} query completed for {}", self.name(), query_type, target));
                    Ok(command_result.stdout)
                } else {
                    let error_msg = format!("{} {} query failed for {} (exit code {}): {}", 
                                          self.name(), query_type, target, command_result.exit_code, command_result.stderr);
                    self.send_log(ui_sender, "ERROR", &error_msg);
                    Err(anyhow::anyhow!(error_msg))
                }
            }
            Err(e) => {
                let error_msg = format!("{} {} command failed for {}: {}", self.name(), query_type, target, e);
                self.send_log(ui_sender, "ERROR", &error_msg);
                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Parse tool output into structured results
    fn parse_output(&self, output: &str, query_type: &str, target: &str) -> Vec<String> {
        // IMPLEMENT: Tool-specific parsing logic
        // Common patterns:
        // - Line-by-line processing: output.lines()
        // - Regex extraction: regex.captures(line)
        // - JSON parsing: serde_json::from_str(output)
        // - XML parsing: roxmltree::Document::parse(output)
        // - CSV parsing: csv::Reader::from_reader(output.as_bytes())
        
        let mut results = Vec::new();
        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            
            // Example parsing logic - customize for your tool
            if self.is_valid_result(line, query_type) {
                let formatted_result = self.format_result(line, query_type, target);
                results.push(formatted_result);
            }
        }
        results
    }

    /// Write plugin results to scans directory
    fn write_results(&self, results: &[(String, Vec<String>)], scans_dir: &std::path::Path, target: &str) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== {} Results for {} ===\n", self.name(), target));
        content.push_str(&format!("Timestamp: {}\n\n", Utc::now()));
        
        let mut total_results = 0;
        for (query_type, query_results) in results {
            if !query_results.is_empty() {
                content.push_str(&format!("=== {} Results ===\n", query_type));
                for result in query_results {
                    content.push_str(&format!("{}\n", result));
                    total_results += 1;
                }
                content.push_str("\n");
            }
        }
        
        content.push_str(&format!("Total results found: {}\n", total_results));
        
        let result_file = scans_dir.join(format!("{}_results.txt", self.name()));
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        Ok(())
    }

    // IMPLEMENT: Tool-specific methods
    
    /// Return the command name for this tool
    fn get_command_name(&self) -> &str {
        // IMPLEMENT: Return the actual command name
        // Examples: "nmap", "dig", "curl", "masscan", "ffuf"
        "your_command"
    }

    /// Build command-line arguments for the tool
    fn build_arguments(&self, target: &str, query_type: &str) -> Vec<String> {
        // IMPLEMENT: Construct arguments based on target and query type
        // Common patterns:
        // - Simple: vec![target.to_string()]
        // - With options: vec!["-option", "value", target]
        // - Conditional: if condition { vec!["-flag"] } else { vec![] }
        vec![target.to_string()]
    }

    /// Get supported query types for this tool
    fn get_supported_query_types(&self) -> Vec<&str> {
        // IMPLEMENT: Return query types this tool supports
        // Examples:
        // - DNS: vec!["A", "AAAA", "MX", "NS", "TXT"]
        // - Port scan: vec!["TCP", "UDP", "SYN"] 
        // - HTTP: vec!["GET", "POST", "HEAD"]
        vec!["default"]
    }

    /// Get the network protocol this tool discovers
    fn get_protocol(&self) -> Proto {
        // IMPLEMENT: Return the primary protocol
        // Proto::Tcp for TCP services
        // Proto::Udp for UDP services
        Proto::Tcp
    }

    /// Get delay between queries in milliseconds
    fn get_query_delay(&self) -> u64 {
        // IMPLEMENT: Return appropriate delay
        // Consider rate limiting and server politeness
        // 250ms for fast tools, 500ms+ for slower tools
        250
    }

    /// Check if a parsed line represents a valid result
    fn is_valid_result(&self, line: &str, query_type: &str) -> bool {
        // IMPLEMENT: Validation logic for parsed results
        // Examples:
        // - IP validation: line.parse::<std::net::IpAddr>().is_ok()
        // - Contains pattern: line.contains("open")
        // - Length check: line.len() > 5
        // - Format check: line.matches(':').count() == 1
        !line.is_empty()
    }

    /// Format a result for consistent output
    fn format_result(&self, line: &str, query_type: &str, target: &str) -> String {
        // IMPLEMENT: Format result for display and storage
        // Common patterns:
        // - Simple: format!("{}: {}", query_type, line)
        // - Detailed: format!("{} -> {} ({})", target, result, query_type)
        // - Structured: format!("{}:{} {} [{}]", host, port, service, protocol)
        format!("{}: {}", query_type, line)
    }
}

#[async_trait]
impl PortScan for {PluginName}Plugin {
    fn name(&self) -> &'static str {
        // IMPLEMENT: Return plugin identifier (lowercase, no spaces)
        "{plugin_name_lowercase}"
    }

    async fn run(&self, state: &mut RunState, _config: &GlobalConfig) -> Result<Vec<Service>> {
        let target = &state.target;
        let ui_sender = state.ui_sender.as_ref().ok_or_else(|| anyhow::anyhow!("No UI sender available"))?;
        let dirs = state.dirs.as_ref().ok_or_else(|| anyhow::anyhow!("No directories available"))?;
        
        // Step 1: Initialization and validation
        self.send_log(ui_sender, "INFO", &format!("Starting {} scan for target: {}", self.name(), target));
        
        if !self.validate_target(target) {
            let error_msg = format!("Invalid target '{}' for {}", target, self.name());
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        let mut services = Vec::new();
        let mut all_results = Vec::new();
        
        // Step 2: Determine query strategy
        let query_types = self.determine_query_types(target);
        self.send_log(ui_sender, "INFO", &format!("Running {} query types", query_types.len()));
        
        // Step 3: Execute queries
        for query_type in &query_types {
            match self.execute_tool(target, query_type, ui_sender).await {
                Ok(output) => {
                    let parsed_results = self.parse_output(&output, query_type, target);
                    
                    if parsed_results.is_empty() {
                        self.send_log(ui_sender, "WARN", &format!("No {} results found for {}", query_type, target));
                    } else {
                        // Step 4: Process and report results
                        for result in &parsed_results {
                            self.send_log(ui_sender, "INFO", &format!("{} result: {}", query_type, result));
                            
                            // Send to UI with tool prefix for identification
                            let _ = ui_sender.send(UiEvent::PortDiscovered {
                                port: self.get_default_port(),
                                service: format!("{} {} - {}", self.name(), query_type, result),
                            });
                        }
                        
                        // Store for file output
                        all_results.push((query_type.to_string(), parsed_results));
                        
                        // Create service objects
                        let service = Service {
                            proto: self.get_protocol(),
                            port: self.get_default_port(),
                            name: format!("{}_{}", self.name().to_uppercase(), query_type),
                            secure: false,
                            address: target.to_string(),
                        };
                        
                        services.push(service);
                    }
                }
                Err(_e) => {
                    self.send_log(ui_sender, "WARN", &format!("Continuing after {} failure", query_type));
                }
            }
            
            // Rate limiting between queries
            tokio::time::sleep(tokio::time::Duration::from_millis(self.get_query_delay())).await;
        }
        
        // Step 5: File output
        if !all_results.is_empty() {
            if let Err(e) = self.write_results(&all_results, &dirs.scans, target) {
                self.send_log(ui_sender, "WARN", &format!("Failed to write {} results: {}", self.name(), e));
            } else {
                self.send_log(ui_sender, "INFO", &format!("{} results written to scans directory", self.name()));
            }
        }
        
        // Step 6: Completion
        if services.is_empty() {
            let error_msg = format!("All {} queries failed for target: {}", self.name(), target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }
        
        self.send_log(ui_sender, "INFO", &format!("{} completed successfully. Found {} result types", self.name(), services.len()));
        Ok(services)
    }
}

// Additional helper methods
impl {PluginName}Plugin {
    /// Determine what query types to run based on target
    fn determine_query_types(&self, target: &str) -> Vec<&str> {
        // IMPLEMENT: Logic to select appropriate query types
        // Examples:
        // - For IPs: vec!["PTR"] (reverse DNS)
        // - For domains: vec!["A", "AAAA", "MX"]
        // - For URLs: vec!["GET", "HEAD"]
        // - For ports: vec!["TCP", "UDP"]
        
        let is_ip = target.parse::<std::net::IpAddr>().is_ok();
        if is_ip {
            // IP-specific queries
            vec!["reverse"]
        } else {
            // Domain/hostname queries
            self.get_supported_query_types()
        }
    }

    /// Get default port number for this tool's discoveries
    fn get_default_port(&self) -> u16 {
        // IMPLEMENT: Return logical port for this tool type
        // Examples: 53 for DNS, 80 for HTTP, 22 for SSH, 443 for HTTPS
        80
    }
}
```

## CONFIGURATION_INTEGRATION

### CONFIGURATION_PHILOSOPHY
Each plugin needs configuration to be customizable without code changes:

1. **Command Configuration**: Tool path and base arguments
2. **Behavior Options**: Query types, delays, retry logic
3. **Limits**: Timeouts, retries, rate limiting
4. **Output Settings**: File formats, verbosity levels

### GLOBAL_TOML_SECTION
```toml
[tools.{plugin_name}]
command = "{command_name}"           # Executable name or path
base_args = ["{arg1}", "{arg2}"]     # Default arguments

[tools.{plugin_name}.options]
query_types = ["type1", "type2"]     # Supported query types
enable_feature = true                # Boolean options
delay_between_queries_ms = 250       # Timing configuration
max_results = 100                    # Result limitations

[tools.{plugin_name}.limits]
timeout_ms = 10000                   # Per-query timeout
max_retries = 2                      # Retry attempts
total_timeout_ms = 30000             # Total plugin timeout
```

### CONFIG_STRUCT_PATTERN
Add to `src/config/types.rs`:

```rust
// Add to ToolsConfig struct
pub {plugin_name}: {PluginName}Config,

// Configuration structures
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Config {
    pub command: String,
    pub base_args: Vec<String>,
    pub options: {PluginName}Options,
    pub limits: {PluginName}Limits,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Options {
    // Tool-specific options based on capabilities
    pub query_types: Vec<String>,
    pub enable_feature: bool,
    pub delay_between_queries_ms: u64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Limits {
    pub timeout_ms: u64,
    pub max_retries: u32,
    pub total_timeout_ms: u64,
}

// Default implementations
impl Default for {PluginName}Config {
    fn default() -> Self {
        Self {
            command: "{command_name}".to_string(),
            base_args: vec![],
            options: {PluginName}Options::default(),
            limits: {PluginName}Limits::default(),
        }
    }
}
```

## INTEGRATION_POINTS

### MODULE_REGISTRATION
```rust
// In src/plugins/mod.rs
pub mod {plugin_name};
```

### SCHEDULER_INTEGRATION
```rust
// In src/core/scheduler.rs execute_plugin_phase_without_ui_start()
let plugin_clone: Box<dyn PortScan> = match plugin_name {
    "existing_plugin" => Box::new(crate::plugins::existing::ExistingPlugin),
    "{plugin_name}" => Box::new(crate::plugins::{plugin_name}::{PluginName}Plugin),
    _ => continue,
};
```

### REGISTRY_INTEGRATION
```rust
// In src/plugins/registry.rs
recon_plugins: vec![
    Box::new(crate::plugins::existing::ExistingPlugin),
    Box::new(crate::plugins::{plugin_name}::{PluginName}Plugin),
],

// Tool validation
fn get_plugin_tools(&self, plugin_name: &str) -> Result<Vec<String>> {
    let tools = match plugin_name {
        "existing" => vec!["existing_cmd".to_string()],
        "{plugin_name}" => vec!["{command_name}".to_string()],
        _ => vec![],
    };
    Ok(tools)
}
```

## TESTING_STRATEGY

### UNIT_TESTING_TEMPLATE
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_target_validation() {
        let plugin = {PluginName}Plugin;
        // Test valid targets
        assert!(plugin.validate_target("valid_target"));
        // Test invalid targets
        assert!(!plugin.validate_target("invalid target"));
    }
    
    #[test]
    fn test_argument_construction() {
        let plugin = {PluginName}Plugin;
        let args = plugin.build_arguments("target", "query_type");
        assert!(!args.is_empty());
        assert!(args.contains(&"target".to_string()));
    }
    
    #[test]
    fn test_output_parsing() {
        let plugin = {PluginName}Plugin;
        let sample_output = "sample tool output here";
        let results = plugin.parse_output(sample_output, "query_type", "target");
        // Add assertions based on expected parsing behavior
    }
    
    #[test]
    fn test_query_type_determination() {
        let plugin = {PluginName}Plugin;
        let ip_queries = plugin.determine_query_types("192.168.1.1");
        let domain_queries = plugin.determine_query_types("example.com");
        // Verify different query strategies
    }
}
```

## IMPLEMENTATION_CHECKLIST

### CORE_IMPLEMENTATION
- [ ] Define plugin struct with `#[derive(Clone)]`
- [ ] Implement `PortScan` trait with `name()` and `run()` methods
- [ ] Add target validation logic in `validate_target()`
- [ ] Implement UI communication with `send_log()`
- [ ] Create tool execution method `execute_tool()`
- [ ] Build output parsing logic in `parse_output()`
- [ ] Add file output functionality in `write_results()`

### TOOL_CONFIGURATION
- [ ] Implement `get_command_name()` returning executable name
- [ ] Build `build_arguments()` for command construction
- [ ] Define `get_supported_query_types()` for capabilities
- [ ] Set `get_protocol()` for service classification
- [ ] Configure `get_query_delay()` for rate limiting
- [ ] Add `determine_query_types()` for smart query selection

### SYSTEM_INTEGRATION
- [ ] Create configuration structs in `config/types.rs`
- [ ] Add plugin config to `ToolsConfig` struct
- [ ] Update `ToolsConfig` Default implementation
- [ ] Add module declaration to `plugins/mod.rs`
- [ ] Register plugin in `scheduler.rs` cloning logic
- [ ] Add plugin to `registry.rs` for validation and inventory
- [ ] Add plugin name to dashboard color rendering in `dashboard/renderer.rs` (line ~512)
  - Update the `tool_color` check to include your plugin name with trailing space
  - Example: Add `|| tool_part.contains("your_plugin ")` to the condition

### QUALITY_ASSURANCE
- [ ] Write comprehensive unit tests
- [ ] Test target validation edge cases
- [ ] Verify output parsing with sample data
- [ ] Test configuration loading
- [ ] Verify UI event integration
- [ ] Test concurrent execution compatibility
- [ ] Validate scan file creation
- [ ] Test error handling and recovery

## COMMON_PATTERNS

### DNS_TOOLS_PATTERN
```rust
// Query types based on target type
let is_ip = target.parse::<std::net::IpAddr>().is_ok();
let query_types = if is_ip {
    vec!["PTR"]  // Reverse DNS for IPs
} else {
    vec!["A", "AAAA", "MX", "NS", "TXT"]  // Forward DNS for domains
};
```

### HTTP_TOOLS_PATTERN
```rust
// Different approaches for HTTP tools
fn build_arguments(&self, target: &str, query_type: &str) -> Vec<String> {
    let mut args = vec!["-s".to_string()]; // Silent mode
    match query_type {
        "GET" => args.extend(vec!["-X", "GET"]),
        "HEAD" => args.extend(vec!["-I"]),
        _ => {}
    }
    args.push(target.to_string());
    args
}
```

### PORT_SCANNER_PATTERN
```rust
// Parse port scanner output
fn parse_output(&self, output: &str, query_type: &str, target: &str) -> Vec<String> {
    let mut results = Vec::new();
    for line in output.lines() {
        if line.contains("open") {
            if let Some(port) = extract_port_from_line(line) {
                results.push(format!("{}:{} open", target, port));
            }
        }
    }
    results
}
```

### SERVICE_ENUMERATION_PATTERN
```rust
// Service-specific probing
fn determine_query_types(&self, target: &str) -> Vec<&str> {
    if target.contains(":") {
        // Target includes port, probe service directly
        vec!["service_probe"]
    } else {
        // Determine service from context or configuration
        vec!["discovery", "enumeration"]
    }
}
```

## DESIGN_PRINCIPLES

### RELIABILITY
- **Graceful Degradation**: Continue on partial failures
- **Error Reporting**: Always log failures with context
- **Timeout Handling**: Prevent hanging on unresponsive tools
- **Resource Cleanup**: Ensure proper cleanup on failures

### PERFORMANCE
- **Concurrent Compatibility**: Support parallel execution
- **Rate Limiting**: Respect target servers and avoid rate limiting
- **Memory Efficiency**: Stream large outputs, don't load everything
- **Caching**: Cache repeated queries when appropriate

### USABILITY
- **Progress Feedback**: Provide real-time status updates
- **Clear Logging**: Use appropriate log levels (INFO/WARN/ERROR)
- **Tool Prefixes**: Identify result sources in UI
- **File Organization**: Create organized, timestamped output files

### MAINTAINABILITY
- **Configuration Driven**: Avoid hardcoded values
- **Modular Design**: Separate validation, execution, parsing, output
- **Comprehensive Testing**: Cover edge cases and error conditions
- **Documentation**: Comment complex parsing and validation logic

This specification provides a comprehensive, tool-agnostic guide for implementing any type of reconnaissance plugin in the ipcrawler system, focusing on the general process and patterns rather than specific tool implementations.