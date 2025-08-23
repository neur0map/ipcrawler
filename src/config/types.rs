use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GlobalConfig {
    pub metadata: Option<MetadataConfig>,
    pub concurrency: ConcurrencyConfig,
    pub tools: ToolsConfig,
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
            tools: ToolsConfig::default(),
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
    pub nmap: NmapConfig,
    pub http_probe: HttpProbeConfig,
    #[serde(flatten)]
    pub custom_tools: HashMap<String, CustomToolConfig>,
}

impl Default for ToolsConfig {
    fn default() -> Self {
        Self {
            nmap: NmapConfig::default(),
            http_probe: HttpProbeConfig::default(),
            custom_tools: HashMap::new(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NmapConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub port_strategy: PortStrategy,
    pub ports: PortConfig,
    pub options: NmapOptions,
    pub limits: NmapLimits,
}

impl Default for NmapConfig {
    fn default() -> Self {
        Self {
            command: "nmap".to_string(),
            base_args: vec!["-sT".to_string(), "-sV".to_string(), "-T4".to_string()],
            port_strategy: PortStrategy::Default,
            ports: PortConfig::default(),
            options: NmapOptions::default(),
            limits: NmapLimits::default(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum PortStrategy {
    Default,
    Top,
    Range,
    List,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PortConfig {
    pub top_ports: Option<u16>,
    pub range_start: Option<u16>,
    pub range_end: Option<u16>,
    pub specific_ports: Option<Vec<u16>>,
}

impl Default for PortConfig {
    fn default() -> Self {
        Self {
            top_ports: Some(1000),
            range_start: None,
            range_end: None,
            specific_ports: None,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NmapOptions {
    pub output_format: String,
    pub timing_template: String,
    pub service_detection: bool,
    pub os_detection: bool,
    pub script_scan: bool,
    pub stealth_mode: bool,
}

impl Default for NmapOptions {
    fn default() -> Self {
        Self {
            output_format: "xml".to_string(),
            timing_template: "T4".to_string(),
            service_detection: true,
            os_detection: false,
            script_scan: false,
            stealth_mode: false,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NmapLimits {
    pub timeout_ms: u64,
    pub max_retries: u32,
    pub host_timeout_ms: u64,
    pub scan_delay_ms: u64,
}

impl Default for NmapLimits {
    fn default() -> Self {
        Self {
            timeout_ms: 300000, // 5 minutes
            max_retries: 2,
            host_timeout_ms: 90000, // 90 seconds
            scan_delay_ms: 0,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HttpProbeConfig {
    pub command: String,
    pub base_args: Vec<String>,
    pub options: HttpProbeOptions,
    pub ssl: HttpProbeSSL,
    pub output: HttpProbeOutput,
    pub limits: HttpProbeLimits,
}

impl Default for HttpProbeConfig {
    fn default() -> Self {
        Self {
            command: "curl".to_string(),
            base_args: vec!["-s".to_string(), "-L".to_string(), "-I".to_string()],
            options: HttpProbeOptions::default(),
            ssl: HttpProbeSSL::default(),
            output: HttpProbeOutput::default(),
            limits: HttpProbeLimits::default(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HttpProbeOptions {
    pub follow_redirects: bool,
    pub silent_mode: bool,
    pub headers_only: bool,
    pub max_redirects: u32,
    pub include_headers: bool,
    pub user_agent: String,
    pub connect_timeout_s: u32,
    pub max_time_s: u32,
}

impl Default for HttpProbeOptions {
    fn default() -> Self {
        Self {
            follow_redirects: true,
            silent_mode: true,
            headers_only: true,
            max_redirects: 10,
            include_headers: true,
            user_agent: "ipcrawler/0.1.0".to_string(),
            connect_timeout_s: 10,
            max_time_s: 15,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HttpProbeSSL {
    pub verify_cert: bool,
    pub ssl_protocols: Vec<String>,
}

impl Default for HttpProbeSSL {
    fn default() -> Self {
        Self {
            verify_cert: false,
            ssl_protocols: vec!["TLSv1.2".to_string(), "TLSv1.3".to_string()],
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HttpProbeOutput {
    pub verbose: bool,
    pub write_response: bool,
    pub include_timing: bool,
}

impl Default for HttpProbeOutput {
    fn default() -> Self {
        Self {
            verbose: false,
            write_response: true,
            include_timing: true,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HttpProbeLimits {
    pub timeout_ms: u64,
    pub max_retries: u32,
    pub connection_timeout_ms: u64,
}

impl Default for HttpProbeLimits {
    fn default() -> Self {
        Self {
            timeout_ms: 15000, // 15 seconds
            max_retries: 1,
            connection_timeout_ms: 10000, // 10 seconds
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CustomToolConfig {
    pub enabled: bool,
    pub command: String,
    pub base_args: Vec<String>,
    pub timeout_ms: u64,
}

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

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OutputConfig {
    pub report_formats: Vec<String>,
    pub default_template: String,
    pub naming: OutputNaming,
    pub retention: OutputRetention,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OutputNaming {
    pub run_id_pattern: String,
    pub timestamp_format: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OutputRetention {
    pub keep_raw_scans: bool,
    pub keep_plugin_results: bool,
    pub compress_old_runs: bool,
    pub max_run_history: u32,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct LoggingConfig {
    pub level: String,
    pub target: String,
    pub max_file_size_mb: u32,
    pub rotate_files: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ValidationConfig {
    pub require_tools: Vec<String>,
    pub check_file_descriptors: bool,
    pub check_disk_space_mb: u64,
    pub targets: TargetValidation,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TargetValidation {
    pub allow_private_ips: bool,
    pub allow_localhost: bool,
    pub max_target_length: usize,
    pub validate_dns: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PluginsConfig {
    pub auto_discover: bool,
    pub plugin_dirs: Vec<String>,
    pub execution_order: ExecutionOrder,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ExecutionOrder {
    pub port_scanners: Vec<String>,
    pub service_scanners: Vec<String>,
    pub reporters: Vec<String>,
}