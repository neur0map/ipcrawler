use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GlobalConfig {
    pub metadata: Option<MetadataConfig>,
    pub concurrency: ConcurrencyConfig,
    pub tools: Option<ToolsConfig>,
    pub overrides: Option<OverridesConfig>,
    pub output: Option<OutputConfig>,
    pub logging: Option<LoggingConfig>,
    pub validation: Option<ValidationConfig>,
    pub plugins: Option<PluginsConfig>,
}

impl Default for GlobalConfig {
    fn default() -> Self {
        Self {
            metadata: None,
            concurrency: ConcurrencyConfig::default(),
            tools: None,
            overrides: None,
            output: None,
            logging: None,
            validation: None,
            plugins: None,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct MetadataConfig {
    pub version: String,
    pub description: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ConcurrencyConfig {
    pub max_total_scans: usize,
    pub max_port_scans: usize,
    pub max_service_scans: usize,
    pub min_file_descriptors: usize,
    pub recommended_file_descriptors: usize,
}

impl Default for ConcurrencyConfig {
    fn default() -> Self {
        Self {
            max_total_scans: 50,
            max_port_scans: 10,
            max_service_scans: 40,
            min_file_descriptors: 1024,
            recommended_file_descriptors: 2048,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ToolsConfig {
    pub nslookup: NslookupConfig,
    pub dig: DigConfig,
    #[serde(flatten)]
    pub custom_tools: HashMap<String, CustomToolConfig>,
}

impl Default for ToolsConfig {
    fn default() -> Self {
        Self {
            nslookup: NslookupConfig::default(),
            dig: DigConfig::default(),
            custom_tools: HashMap::new(),
        }
    }
}

// ========================================
// NSLOOKUP CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NslookupConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub options: NslookupOptions,
    pub limits: NslookupLimits,
}

impl Default for NslookupConfig {
    fn default() -> Self {
        Self {
            command: "nslookup".to_string(),
            base_args: vec![],
            options: NslookupOptions::default(),
            limits: NslookupLimits::default(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NslookupOptions {
    pub record_types: Vec<String>,
    pub reverse_dns: bool,
    pub recursive: bool,
    pub delay_between_queries_ms: u64,
}

impl Default for NslookupOptions {
    fn default() -> Self {
        Self {
            record_types: vec![
                "A".to_string(), "AAAA".to_string(), "MX".to_string(), 
                "NS".to_string(), "TXT".to_string(), "PTR".to_string()
            ],
            reverse_dns: true,
            recursive: true,
            delay_between_queries_ms: 500,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NslookupLimits {
    pub timeout_ms: u64,
    pub max_retries: u32,
    pub total_timeout_ms: u64,
}

impl Default for NslookupLimits {
    fn default() -> Self {
        Self {
            timeout_ms: 10000,
            max_retries: 2,
            total_timeout_ms: 30000,
        }
    }
}

// ========================================
// DIG CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DigConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub options: DigOptions,
    pub limits: DigLimits,
}

impl Default for DigConfig {
    fn default() -> Self {
        Self {
            command: "dig".to_string(),
            base_args: vec!["+short".to_string(), "+time=3".to_string(), "+tries=2".to_string()],
            options: DigOptions::default(),
            limits: DigLimits::default(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DigOptions {
    pub record_types: Vec<String>,
    pub reverse_dns: bool,
    pub recursive: bool,
    pub delay_between_queries_ms: u64,
    pub include_additional_records: bool,
}

impl Default for DigOptions {
    fn default() -> Self {
        Self {
            record_types: vec![
                "A".to_string(), "AAAA".to_string(), "MX".to_string(), 
                "NS".to_string(), "TXT".to_string(), "CNAME".to_string(), 
                "SOA".to_string(), "PTR".to_string()
            ],
            reverse_dns: true,
            recursive: true,
            delay_between_queries_ms: 250,
            include_additional_records: false,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DigLimits {
    pub timeout_ms: u64,
    pub max_retries: u32,
    pub total_timeout_ms: u64,
    pub query_timeout_ms: u64,
}

impl Default for DigLimits {
    fn default() -> Self {
        Self {
            timeout_ms: 10000,
            max_retries: 2,
            total_timeout_ms: 30000,
            query_timeout_ms: 3000,
        }
    }
}

// ========================================
// CUSTOM TOOL CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CustomToolConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub timeout_ms: u64,
    pub max_retries: u32,
}

impl Default for CustomToolConfig {
    fn default() -> Self {
        Self {
            command: "custom_tool".to_string(),
            base_args: vec![],
            timeout_ms: 30000,
            max_retries: 2,
        }
    }
}

// ========================================
// GLOBAL OVERRIDES
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OverridesConfig {
    pub paths: Option<HashMap<String, String>>,
    pub env: Option<HashMap<String, String>>,
    pub timeouts: Option<TimeoutOverrides>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TimeoutOverrides {
    pub multiplier: f64,
    pub max_total_runtime_s: u64,
}

impl Default for TimeoutOverrides {
    fn default() -> Self {
        Self {
            multiplier: 1.0,
            max_total_runtime_s: 300, // 5 minutes
        }
    }
}

// ========================================
// OUTPUT CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OutputConfig {
    pub report_formats: Vec<String>,
    pub default_template: String,
    pub naming: Option<NamingConfig>,
    pub retention: Option<RetentionConfig>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NamingConfig {
    pub run_id_pattern: String,
    pub timestamp_format: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RetentionConfig {
    pub keep_raw_scans: bool,
    pub keep_plugin_results: bool,
    pub compress_old_runs: bool,
    pub max_run_history: u32,
}

// ========================================
// LOGGING CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct LoggingConfig {
    pub level: String,
    pub target: String,
    pub max_file_size_mb: u64,
    pub rotate_files: bool,
}

// ========================================
// VALIDATION CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ValidationConfig {
    pub require_tools: Vec<String>,
    pub check_file_descriptors: bool,
    pub check_disk_space_mb: u64,
    pub targets: Option<TargetValidation>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TargetValidation {
    pub allow_private_ips: bool,
    pub allow_localhost: bool,
    pub max_target_length: usize,
    pub validate_dns: bool,
}

// ========================================
// PLUGINS CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PluginsConfig {
    pub auto_discover: bool,
    pub plugin_dirs: Vec<String>,
    pub execution_order: Option<ExecutionOrder>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ExecutionOrder {
    pub reconnaissance: Vec<String>,
    pub port_scanners: Vec<String>,
    pub service_scanners: Vec<String>,
    pub reporters: Vec<String>,
}