# ipcrawler Plugin Implementation Specification v2.0
# Machine-readable plugin development guide for AI coders

## ARCHITECTURE_OVERVIEW

The ipcrawler system supports **reconnaissance plugins** that implement either `PortScan` or `ServiceScan` traits. All plugins run concurrently, provide real-time UI feedback, and create persistent scan results.

**Plugin Trait Types:**
- **PortScan**: Target-based plugins that discover services from IP/domain targets
- **ServiceScan**: Service-based plugins that analyze discovered services in detail

**Current Plugin Types:**
- **DNS Reconnaissance** (PortScan) - Query DNS records and resolve hostnames
- **Network Discovery** (PortScan) - Identify open ports and services  
- **Service Enumeration** (ServiceScan) - Probe specific services for details
- **Web Application Analysis** (ServiceScan) - Directory enumeration and content analysis

## PLUGIN_DEVELOPMENT_PROCESS

### STEP_1_ANALYSIS_PHASE
Before coding, analyze your target tool:

1. **Command Structure**: How does the tool accept arguments?
2. **Output Format**: What does the tool's output look like?
3. **Error Conditions**: How does the tool indicate failures?
4. **Record Types**: What types of information does it discover?
5. **Target Support**: Does it handle IPs, domains, or both?
6. **Plugin Type**: Does it scan targets (PortScan) or analyze services (ServiceScan)?
7. **Performance Budget**: What time constraints are appropriate for this tool?

### STEP_2_DESIGN_DECISIONS
Make these architectural choices:

1. **Plugin Name**: Choose a clear, lowercase identifier
2. **Plugin Trait**: PortScan (target-based) or ServiceScan (service-based)
3. **Protocol**: Will it discover TCP or UDP services?
4. **Record Types**: What information categories will it report?
5. **Query Strategy**: Single query vs multiple queries per target?
6. **Error Tolerance**: Continue on partial failures or stop completely?
7. **Time Budget**: Per-target vs per-service time allocation
8. **Concurrency**: Can it run safely in parallel with other plugins?

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

## PLUGIN_TEMPLATES

### PORTSCAN_TEMPLATE (Target-based discovery)
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

### SERVICESCAN_TEMPLATE (Service-based analysis)
```rust
use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::{RunState, PluginFindings}};
use crate::plugins::types::ServiceScan;
use crate::config::GlobalConfig;
use std::collections::HashMap;
use tokio::time::{sleep, Duration, timeout};

#[derive(Clone)]
pub struct {PluginName}Plugin {
    // Internal configuration and state
    config: {PluginName}Config,
    // Per-service time budget
    time_budget: Duration,
}

#[derive(Debug, Clone)]
struct {PluginName}Config {
    time_budget_sec: u64,
    // Tool-specific configuration
    max_concurrent_operations: usize,
    rate_limit_ms: u64,
}

impl Default for {PluginName}Config {
    fn default() -> Self {
        Self {
            time_budget_sec: 120,  // 2 minutes per service (optimized for CTF/lab)
            max_concurrent_operations: 8,
            rate_limit_ms: 67,  // ~15 requests/second
        }
    }
}

impl {PluginName}Plugin {
    pub fn new(global_config: &GlobalConfig) -> Result<Self> {
        // Parse configuration with graceful fallbacks
        let config = Self::parse_config(global_config)?;
        
        Ok(Self {
            time_budget: Duration::from_secs(config.time_budget_sec),
            config,
        })
    }
    
    fn parse_config(_config: &GlobalConfig) -> Result<{PluginName}Config> {
        // Use internal configuration with graceful fallbacks
        // CRITICAL: Plugin must work without any global.toml configuration
        let config = {PluginName}Config::default();
        Ok(config)
    }
    
    /// Check if this plugin should analyze the given service
    fn should_analyze_service(&self, service: &Service) -> bool {
        // IMPLEMENT: Service filtering logic
        // Examples:
        // - HTTP services: service.name.to_lowercase().contains("http")
        // - Specific ports: vec![80, 443, 8080].contains(&service.port)
        // - Protocol match: service.proto == Proto::Tcp
        // - Service patterns: service.name.contains("web") || service.name.contains("http")
        
        match service.port {
            80 | 443 | 8080 | 8443 => true,  // Common web ports
            _ => service.name.to_lowercase().contains("http"),
        }
    }
    
    /// Execute the main analysis workflow with time budget
    async fn execute_analysis(&self, service: &Service, state: &RunState) -> Result<Option<PluginFindings>> {
        let start_time = std::time::Instant::now();
        let mut findings = HashMap::new();
        
        // Phase-based execution with time budget allocation
        // Phase 1: Initial reconnaissance (25% of budget)
        let phase1_budget = self.time_budget / 4;
        if let Ok(recon_results) = timeout(phase1_budget, self.phase_initial_recon(service, state)).await {
            if let Ok(results) = recon_results {
                findings.extend(results);
            }
        }
        
        // Phase 2: Deep analysis (50% of budget) 
        let remaining = self.time_budget.saturating_sub(start_time.elapsed());
        let phase2_budget = remaining / 2;
        if let Ok(analysis_results) = timeout(phase2_budget, self.phase_deep_analysis(service, state, &findings)).await {
            if let Ok(results) = analysis_results {
                findings.extend(results);
            }
        }
        
        // Phase 3: Content retrieval (25% of remaining budget)
        let remaining = self.time_budget.saturating_sub(start_time.elapsed());
        if remaining > Duration::from_secs(5) {  // At least 5 seconds left
            if let Ok(content_results) = timeout(remaining, self.phase_content_retrieval(service, state, &findings)).await {
                if let Ok(results) = content_results {
                    findings.extend(results);
                }
            }
        }
        
        if findings.is_empty() {
            Ok(None)
        } else {
            Ok(Some(PluginFindings {
                plugin_name: self.name().to_string(),
                target: format!("{}:{}", service.address, service.port),
                findings,
                metadata: self.create_metadata(start_time.elapsed()),
            }))
        }
    }
    
    // Phase implementation methods - IMPLEMENT for your specific tool
    async fn phase_initial_recon(&self, service: &Service, _state: &RunState) -> Result<HashMap<String, String>> {
        // IMPLEMENT: Initial service reconnaissance
        todo!("Implement initial reconnaissance phase")
    }
    
    async fn phase_deep_analysis(&self, service: &Service, _state: &RunState, initial_findings: &HashMap<String, String>) -> Result<HashMap<String, String>> {
        // IMPLEMENT: Deep analysis based on initial findings
        todo!("Implement deep analysis phase")
    }
    
    async fn phase_content_retrieval(&self, service: &Service, _state: &RunState, previous_findings: &HashMap<String, String>) -> Result<HashMap<String, String>> {
        // IMPLEMENT: Content retrieval and analysis
        todo!("Implement content retrieval phase")
    }
    
    fn create_metadata(&self, elapsed: Duration) -> HashMap<String, String> {
        let mut metadata = HashMap::new();
        metadata.insert("execution_time_ms".to_string(), elapsed.as_millis().to_string());
        metadata.insert("time_budget_ms".to_string(), self.time_budget.as_millis().to_string());
        metadata.insert("plugin_version".to_string(), "1.0.0".to_string());
        metadata
    }
}

#[async_trait]
impl ServiceScan for {PluginName}Plugin {
    fn name(&self) -> &'static str {
        "{plugin_name_lowercase}"
    }
    
    fn matches(&self, service: &Service) -> bool {
        self.should_analyze_service(service)
    }
    
    async fn run(&self, service: &Service, state: &RunState, _config: &GlobalConfig) -> Result<Option<PluginFindings>> {
        // Execute analysis with comprehensive error handling
        match self.execute_analysis(service, state).await {
            Ok(findings) => Ok(findings),
            Err(e) => {
                tracing::warn!("Plugin {} failed on {}:{}: {}", 
                    self.name(), service.address, service.port, e);
                Ok(None)  // Don't fail the entire scan for one service
            }
        }
    }
}
```

### PERFORMANCE_OPTIMIZATION_PATTERNS

Based on real-world implementation experience, here are critical performance patterns discovered during looter plugin development:

#### TIME_BUDGET_ALLOCATION
```rust
// Allocate time budget across phases for optimal results
// Key insight: 2-minute budgets work well for CTF/lab environments
impl TimeBudget {
    fn allocate_phases(total_seconds: u64) -> HashMap<Phase, Duration> {
        let mut allocations = HashMap::new();
        allocations.insert(Phase::Seeds, 0.15);      // 15% - Quick reconnaissance
        allocations.insert(Phase::Baseline, 0.25);   // 25% - Core discovery
        allocations.insert(Phase::Enhanced, 0.30);   // 30% - Deep analysis
        allocations.insert(Phase::Retrieval, 0.20);  // 20% - Content retrieval
        allocations.insert(Phase::Analysis, 0.10);   // 10% - Final processing
        
        allocations.into_iter()
            .map(|(phase, ratio)| (phase, Duration::from_secs((total_seconds as f64 * ratio) as u64)))
            .collect()
    }
}
```

#### PARALLEL_PROCESSING_PATTERN
```rust
// For ServiceScan plugins running on multiple discovered services
// Key insight: Use semaphores for concurrency control, not sequential execution
use tokio::sync::Semaphore;
use std::sync::Arc;

async fn execute_parallel_service_analysis(
    services: Vec<Service>,
    plugin: Arc<dyn ServiceScan>,
    max_concurrent: usize,
) -> Vec<Result<Option<PluginFindings>>> {
    let semaphore = Arc::new(Semaphore::new(max_concurrent));
    let mut tasks = Vec::new();
    
    for service in services {
        let permit = semaphore.clone().acquire_owned().await.unwrap();
        let plugin_clone = plugin.clone();
        let service_clone = service.clone();
        
        let task = tokio::spawn(async move {
            let _permit = permit;
            plugin_clone.run(&service_clone, &state, &config).await
        });
        
        tasks.push(task);
    }
    
    let mut results = Vec::new();
    for task in tasks {
        match task.await {
            Ok(result) => results.push(result),
            Err(e) => results.push(Err(anyhow::anyhow!("Task failed: {}", e))),
        }
    }
    
    results
}
```

#### GRACEFUL_DEGRADATION_PATTERN  
```rust
// Handle timeouts and failures gracefully without losing progress
// Key insight: Configuration crashes were caused by TOML parsing, not runtime errors
impl YourPlugin {
    async fn execute_with_graceful_fallback<T>(&self, operation: impl Future<Output = Result<T>>) -> Option<T> {
        match operation.await {
            Ok(result) => Some(result),
            Err(e) => {
                tracing::debug!("Operation failed gracefully: {}", e);
                None  // Continue with partial results instead of failing entire plugin
            }
        }
    }
    
    // CRITICAL: All plugins must work without global.toml configuration
    fn get_config_with_fallback(global_config: &GlobalConfig) -> YourPluginConfig {
        global_config.tools
            .as_ref()
            .and_then(|tools| tools.your_plugin.as_ref())
            .cloned()
            .unwrap_or_else(YourPluginConfig::default)  // Always provide working defaults
    }
}
```

## CONFIGURATION_INTEGRATION

### CONFIGURATION_PHILOSOPHY
Each plugin follows a two-tier configuration system:

1. **Built-in Defaults**: Plugins have sensible defaults hardcoded
2. **Global.toml Overrides**: ALL configurations in global.toml are COMMENTED OUT by default
3. **User Customization**: Users uncomment sections to override specific settings
4. **Plugin Resilience**: Plugins MUST work without any global.toml configuration

**CRITICAL**: The global.toml file is NOT for default configuration - it's purely for overrides!

### GLOBAL_TOML_SECTION
```toml
# ========================================
# {PLUGIN_NAME} CONFIGURATION
# ========================================
# Uncomment any section below to override default plugin behavior

# [tools.{plugin_name}]
# command = "{command_name}"           # Executable name or path
# base_args = ["{arg1}", "{arg2}"]     # Default arguments
# 
# [tools.{plugin_name}.options]
# query_types = ["type1", "type2"]     # Supported query types
# enable_feature = true                # Boolean options
# delay_between_queries_ms = 250       # Timing configuration
# max_results = 100                    # Result limitations
# 
# [tools.{plugin_name}.limits]
# timeout_ms = 10000                   # Per-query timeout
# max_retries = 2                      # Retry attempts
# total_timeout_ms = 30000             # Total plugin timeout
```

**NOTE**: All plugin configurations in global.toml MUST be commented out by default!

### CONFIG_STRUCT_PATTERN
Add to `src/config/types.rs`:

```rust
// Add to ToolsConfig struct - MUST BE OPTIONAL!
pub {plugin_name}: Option<{PluginName}Config>,

// Configuration structures
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct {PluginName}Config {
    pub command: String,
    pub base_args: Vec<String>,
    pub options: Option<{PluginName}Options>,  // Optional for partial overrides
    pub limits: Option<{PluginName}Limits>,    // Optional for partial overrides
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

// Default implementations - CRITICAL FOR PLUGIN OPERATION WITHOUT CONFIG!
impl Default for {PluginName}Config {
    fn default() -> Self {
        Self {
            command: "{command_name}".to_string(),
            base_args: vec![],
            options: Some({PluginName}Options::default()),
            limits: Some({PluginName}Limits::default()),
        }
    }
}

impl Default for {PluginName}Options {
    fn default() -> Self {
        Self {
            query_types: vec!["default".to_string()],
            enable_feature: true,
            delay_between_queries_ms: 250,
        }
    }
}

impl Default for {PluginName}Limits {
    fn default() -> Self {
        Self {
            timeout_ms: 10000,
            max_retries: 2,
            total_timeout_ms: 30000,
        }
    }
}
```

### PLUGIN_CONFIG_ACCESS_PATTERN
```rust
// In your plugin implementation - ALWAYS handle missing configuration!
impl YourPlugin {
    fn get_config<'a>(&self, global_config: &'a GlobalConfig) -> YourPluginConfig {
        global_config.tools
            .as_ref()
            .and_then(|tools| tools.your_plugin.as_ref())
            .cloned()
            .unwrap_or_else(YourPluginConfig::default())
    }
    
    fn get_command(&self, config: &GlobalConfig) -> String {
        let plugin_config = self.get_config(config);
        plugin_config.command
    }
    
    fn get_timeout(&self, config: &GlobalConfig) -> u64 {
        let plugin_config = self.get_config(config);
        plugin_config.limits
            .as_ref()
            .map(|l| l.timeout_ms)
            .unwrap_or(10000)  // Fallback to hardcoded default
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
- [ ] Create configuration structs in `config/types.rs` with `Option<YourPluginConfig>`
- [ ] Add plugin config to `ToolsConfig` struct as OPTIONAL field
- [ ] Implement proper Default traits for all config structs
- [ ] Ensure plugin works WITHOUT any global.toml configuration
- [ ] Add COMMENTED OUT configuration to global.toml (for overrides only)
- [ ] Add module declaration to `plugins/mod.rs`
- [ ] Register plugin in `scheduler.rs` cloning logic
- [ ] Add plugin to `registry.rs` for validation and inventory
- [ ] Add plugin name to dashboard color rendering in `dashboard/renderer.rs` (line ~512)
  - Update the `tool_color` check to include your plugin name with trailing space
  - Example: Add `|| tool_part.contains("your_plugin ")` to the condition
- [ ] **CRITICAL**: Add tool availability check in `registry.rs` for optional tools
  - Implement `{plugin}_tools_available()` function if your plugin depends on external tools
  - Add conditional plugin loading: `if Self::{plugin}_tools_available() { /* add plugin */ }`
  - This prevents plugin loading when required tools are missing
- [ ] **SERVICE SCAN PLUGINS**: If implementing ServiceScan trait (not PortScan):
  - Implement `matches(&self, service: &Service) -> bool` to filter services
  - Use `ServiceScan::run(&self, service: &Service, state: &RunState, config: &GlobalConfig)`
  - Plugin runs per-service, not per-target like PortScan plugins
  - Store findings in `state.plugin_findings` using `insert(plugin_name, findings)`
- [ ] **STDIN-BASED TOOLS**: If your tool requires stdin input (like dnsx/httpx):
  - Implement `execute_with_stdin()` method for piping input to commands
  - DO NOT use regular command-line arguments for input data
  - Use `tokio::process::Command` with `Stdio::piped()` for stdin
  - Tools like `dnsx` and `httpx` from ProjectDiscovery require this pattern
- [ ] **CONFIGURATION INTEGRATION**: For complex tools with multiple sub-tools:
  - Define separate config structs for each sub-tool (e.g., `DnsxConfig`, `HttpxConfig`)
  - Use `Option<YourPluginConfig>` in `ToolsConfig` for optional plugins
  - Implement proper timeout and command path configuration per sub-tool
- [ ] **FILE OUTPUT**: Create comprehensive result files:
  - Use descriptive filenames like `{plugin}_comprehensive.txt` vs `{plugin}_results.txt`
  - Organize output by discovery type (DNS records, HTTP services, etc.)
  - Include summary statistics and metadata (wildcard detection, timestamps)
- [ ] **UI PANEL SEPARATION**: Ensure proper UI integration:
  - **Live Logs Panel**: Use `send_log()` for progress messages only
  - **Results Panel**: Use `UiEvent::PortDiscovered` for actual discoveries
  - Never log individual discoveries - they should only go to Results panel
  - Follow format: `"{plugin} {TYPE} - {discovery_info}"`

### QUALITY_ASSURANCE
- [ ] Write comprehensive unit tests
- [ ] Test target validation edge cases
- [ ] Verify output parsing with sample data
- [ ] Test configuration loading
- [ ] Verify UI event integration
- [ ] Test concurrent execution compatibility
- [ ] Validate scan file creation
- [ ] Test error handling and recovery

## ADVANCED_PATTERNS

### COMPREHENSIVE_DISCOVERY_PATTERN
```rust
// For tools that perform multiple types of discovery (DNS + HTTP + Tech detection)
struct ComprehensivePlugin {
    // Multiple discovery methods
}

impl ComprehensivePlugin {
    /// Run comprehensive discovery based on target type
    async fn run_comprehensive_discovery(&self, target: &str, config: &GlobalConfig) -> Result<DiscoveryResults> {
        let is_ip = target.parse::<std::net::IpAddr>().is_ok();
        let mut all_discoveries = Vec::new();
        
        if is_ip {
            // IP targets: Reverse DNS + HTTP tech detection
            let reverse_results = self.run_reverse_dns(target, config).await?;
            let http_results = self.run_http_discovery(target, config).await?;
            all_discoveries.extend(reverse_results);
            all_discoveries.extend(http_results);
        } else {
            // Domain targets: Forward DNS + HTTP + Chain resolution
            let dns_results = self.run_forward_dns(target, config).await?;
            all_discoveries.extend(dns_results.clone());
            
            // Follow CNAME/MX/NS chains
            for (domain, value) in &dns_results {
                if value.starts_with("CNAME:") {
                    let canonical = value.strip_prefix("CNAME:").unwrap();
                    let chain_results = self.run_forward_dns(canonical, config).await?;
                    all_discoveries.extend(chain_results);
                }
            }
            
            // Run HTTP discovery on discovered IPs
            let unique_ips: HashSet<String> = dns_results.iter()
                .filter_map(|(_, ip)| {
                    if ip.parse::<std::net::IpAddr>().is_ok() { Some(ip.clone()) } else { None }
                })
                .collect();
                
            for ip in unique_ips {
                let http_results = self.run_http_discovery(&ip, config).await?;
                all_discoveries.extend(http_results);
            }
        }
        
        Ok(all_discoveries)
    }
}
```

### STDIN_EXECUTION_PATTERN
```rust
// For tools that require stdin input (dnsx, httpx, etc.)
use tokio::process::Command;
use std::process::Stdio;
use tokio::io::AsyncWriteExt;

impl YourPlugin {
    async fn execute_with_stdin(&self, command: &str, args: &[&str], stdin_input: &str, timeout_ms: u64) -> Result<String> {
        let mut cmd = Command::new(command);
        cmd.args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        let mut child = cmd.spawn()?;

        // Write to stdin - CRITICAL for tools like dnsx/httpx
        if let Some(stdin) = child.stdin.take() {
            let mut stdin = stdin;
            stdin.write_all(stdin_input.as_bytes()).await?;
            stdin.shutdown().await?;
        }

        let output = tokio::time::timeout(
            tokio::time::Duration::from_millis(timeout_ms),
            child.wait_with_output(),
        ).await??;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            Err(anyhow::anyhow!("Command failed: {}", String::from_utf8_lossy(&output.stderr)))
        }
    }
}
```

### OPTIONAL_TOOLS_PATTERN
```rust
// In src/plugins/registry.rs - Add tool availability checks
impl PluginRegistry {
    fn your_plugin_tools_available() -> bool {
        // Check if required external tools are available
        which::which("your_required_tool").is_ok() && 
        which::which("your_second_tool").is_ok()
    }
    
    pub fn new() -> Self {
        let mut recon_plugins = vec![
            // Always available plugins
            Box::new(crate::plugins::dig::DigPlugin),
            Box::new(crate::plugins::nslookup::NslookupPlugin),
        ];
        
        // Conditionally available plugins
        if Self::your_plugin_tools_available() {
            recon_plugins.push(Box::new(crate::plugins::your_plugin::YourPlugin));
        } else {
            tracing::info!("YourPlugin disabled - required tools not available");
        }
        
        Self { recon_plugins, /* ... */ }
    }
}
```

### WILDCARD_DETECTION_PATTERN
```rust
// Prevent false positives from wildcard DNS
impl YourPlugin {
    async fn detect_wildcard_dns(&self, target: &str, config: &GlobalConfig) -> Result<bool> {
        let random_subdomains = vec![
            format!("randomtest12345.{}", target),
            format!("nonexistentabcd.{}", target),
            format!("shouldnotexist9999.{}", target),
        ];
        
        let test_input = random_subdomains.join("\n");
        let result = self.execute_with_stdin("dnsx", &["-silent", "-a"], &test_input, 15000).await?;
        
        Ok(!result.trim().is_empty()) // If random subdomains resolve, wildcard exists
    }
}
```

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

## CONFIGURATION_EXAMPLE

### INCORRECT_APPROACH (DON'T DO THIS)
```toml
# global.toml - WRONG: Active default configuration
[tools.port_scanner]
enabled = true
scan_strategy = "top-1000"  # <-- This is a default, not an override!

[tools.port_scanner.rustscan]
command = "rustscan"
timeout_ms = 1500
```

### CORRECT_APPROACH (DO THIS)
```toml
# global.toml - CORRECT: All commented, acts as override documentation
# ========================================
# PORT SCANNER CONFIGURATION
# ========================================
# Uncomment any section below to override default plugin behavior

# [tools.port_scanner]
# enabled = true           # Override to disable: enabled = false
# scan_strategy = "full"   # Override default top-1000 with full scan
# 
# [tools.port_scanner.rustscan]
# command = "/custom/path/rustscan"  # Override if rustscan is in non-standard location
# timeout_ms = 5000                   # Override for slower networks
```

```rust
// In plugin code - CORRECT: Hardcoded defaults with override capability
impl PortScannerPlugin {
    fn get_scan_strategy(&self, config: &GlobalConfig) -> String {
        config.tools
            .as_ref()
            .and_then(|t| t.port_scanner.as_ref())
            .and_then(|ps| ps.ports.as_ref())
            .map(|p| p.scan_strategy.clone())
            .unwrap_or_else(|| "top-1000".to_string())  // Hardcoded default
    }
}
```

## LESSONS_LEARNED

### CRITICAL_GAPS_ADDRESSED
This specification was enhanced based on real implementation experience with the `hosts_discovery` and `looter` plugins. Key gaps that were identified and addressed:

1. **Tool Availability Checking**: The original spec didn't emphasize conditional plugin loading for optional external tools
2. **Stdin Execution Pattern**: Many modern recon tools (dnsx, httpx) require stdin input, not command arguments
3. **UI Panel Separation**: Critical distinction between Live Logs vs Results panel was underemphasized
4. **Comprehensive Discovery**: Pattern for chaining multiple discovery types and following DNS chains
5. **Wildcard Detection**: Essential for DNS-based tools to prevent false positives
6. **Configuration Complexity**: Multi-tool plugins need more sophisticated config structures
7. **ServiceScan vs PortScan**: ServiceScan plugins analyze discovered services, not targets directly
8. **Performance Optimization**: 2-minute time budgets with parallel processing for CTF/lab efficiency
9. **Configuration Crashes**: TOML parsing failures caused by active configuration sections vs commented defaults
10. **Graceful Error Handling**: Plugins must continue operating with partial failures and missing dependencies

### DEBUGGING_CHECKLIST
If your plugin isn't working as expected:

- [ ] **No Results in UI**: Check that you're sending `UiEvent::PortDiscovered` not just logs
- [ ] **Tool Not Found**: Verify tool availability check in registry.rs
- [ ] **Empty Output**: For stdin tools, ensure you're using `execute_with_stdin()` not regular execution
- [ ] **Color Issues**: Verify plugin name is in dashboard renderer color list
- [ ] **Config Errors**: Check that config structs match TOML structure exactly
- [ ] **Build Failures**: Ensure all imports and async patterns match existing plugins

This specification provides a comprehensive, battle-tested guide for implementing any type of reconnaissance plugin in the ipcrawler system, based on real-world implementation experience and identified gaps in the original specification.