use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
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

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ToolsConfig {
    pub nslookup: Option<NslookupConfig>,
    pub dig: Option<DigConfig>,
    pub hosts_discovery: Option<HostsDiscoveryConfig>,
    pub port_scanner: Option<PortScannerConfig>,
    #[serde(flatten)]
    pub custom_tools: HashMap<String, CustomToolConfig>,
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
                "A".to_string(),
                "AAAA".to_string(),
                "MX".to_string(),
                "NS".to_string(),
                "TXT".to_string(),
                "PTR".to_string(),
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
            base_args: vec![
                "+short".to_string(),
                "+time=3".to_string(),
                "+tries=2".to_string(),
            ],
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
                "A".to_string(),
                "AAAA".to_string(),
                "MX".to_string(),
                "NS".to_string(),
                "TXT".to_string(),
                "CNAME".to_string(),
                "SOA".to_string(),
                "PTR".to_string(),
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
// HOSTS DISCOVERY CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HostsDiscoveryConfig {
    pub enabled: bool,
    pub target_ip: String,
    pub auto_write: bool,
    pub backup_hosts: bool,
    pub dnsx: HostsDiscoveryToolConfig,
    pub httpx: HostsDiscoveryToolConfig,
}

impl Default for HostsDiscoveryConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            target_ip: "127.0.0.1".to_string(),
            auto_write: true,
            backup_hosts: true,
            dnsx: HostsDiscoveryToolConfig {
                command: "dnsx".to_string(),
                timeout_ms: 30000,
                max_results: 1000,
            },
            httpx: HostsDiscoveryToolConfig {
                command: "httpx".to_string(),
                timeout_ms: 60000,
                max_results: 100,
            },
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HostsDiscoveryToolConfig {
    pub command: String,
    pub timeout_ms: u64,
    pub max_results: usize,
}

// ========================================
// PORT SCANNER CONFIGURATION
// ========================================

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PortScannerConfig {
    pub enabled: bool,
    pub ports: Option<PortsConfig>,
    pub rustscan: RustScanConfig,
    pub nmap: NmapConfig,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PortsConfig {
    pub scan_strategy: String,
    pub custom_range: String,
}

impl Default for PortScannerConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            ports: Some(PortsConfig::default()),
            rustscan: RustScanConfig::default(),
            nmap: NmapConfig::default(),
        }
    }
}

impl Default for PortsConfig {
    fn default() -> Self {
        Self {
            scan_strategy: "top-1000".to_string(),
            custom_range: "1-1000".to_string(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RustScanConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub timeout_ms: u64,
    pub total_timeout_ms: u64,
    pub batch_size: u32,
    pub ulimit: u32,
    pub tries: u32,
}

impl Default for RustScanConfig {
    fn default() -> Self {
        Self {
            command: "rustscan".to_string(),
            base_args: vec!["--greppable".to_string()],
            timeout_ms: 3000,
            total_timeout_ms: 300000, // 5 minutes
            batch_size: 4500,
            ulimit: 5000,
            tries: 1,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NmapConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub total_timeout_ms: u64,
    pub version_intensity: u32,
    pub max_retries: u32,
    pub host_timeout_sec: u32,
    pub auto_detect_sudo: bool,
    pub fallback_to_connect_scan: bool,
}

impl Default for NmapConfig {
    fn default() -> Self {
        Self {
            command: "nmap".to_string(),
            base_args: vec!["--open".to_string()],
            total_timeout_ms: 600000, // 10 minutes
            version_intensity: 7,
            max_retries: 2,
            host_timeout_sec: 300, // 5 minutes per host
            auto_detect_sudo: true,
            fallback_to_connect_scan: true,
        }
    }
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
