use crate::executor::ToolResult;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Serialize, Deserialize, Debug)]
pub struct ScanSummary {
    pub metadata: ScanMetadata,
    pub execution_stats: ExecutionStats,
    pub tool_results: Vec<ToolResultSummary>,
    pub discoveries: Vec<Discovery>,
    pub raw_outputs: HashMap<String, RawToolOutput>,
    pub parsing_metadata: ParsingMetadata,
    pub failed_tools: Vec<FailedTool>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ScanMetadata {
    pub target: String,
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub duration_seconds: f64,
    pub output_directory: String,
    pub config_used: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ExecutionStats {
    pub total_tools: usize,
    pub successful_tools: usize,
    pub failed_tools: usize,
    pub tools_with_output: usize,
    pub total_output_size: u64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ToolResultSummary {
    pub name: String,
    pub command: String,
    pub exit_code: i32,
    pub duration_seconds: f64,
    pub has_output: bool,
    pub output_size: u64,
    pub error_message: Option<String>,
}

// Generic discovery structure - replaces hardcoded ports/services
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Discovery {
    pub discovery_type: DiscoveryType,
    pub value: String,
    pub confidence: f32,
    pub metadata: HashMap<String, serde_json::Value>,
    pub detected_by: String,
    pub detection_pattern: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum DiscoveryType {
    Port { number: u16, protocol: String },
    Service { port: u16, protocol: String, name: String, version: Option<String> },
    Host { hostname: String, ip: Option<String> },
    Vulnerability { severity: String, cve: Option<String> },
    Directory { path: String, status: u16 },
    Custom { category: String, subcategory: Option<String> },
}

// Raw tool output storage
#[derive(Serialize, Deserialize, Debug)]
pub struct RawToolOutput {
    pub stdout: String,
    pub stderr: String,
    pub file_paths: Vec<String>,
    pub size_bytes: u64,
    pub parsed_success: bool,
    pub parsing_errors: Vec<String>,
}

// Parsing metadata for transparency
#[derive(Serialize, Deserialize, Debug)]
pub struct ParsingMetadata {
    pub patterns_used: Vec<String>,
    pub total_lines_processed: u64,
    pub successful_extractions: u64,
    pub failed_extractions: u64,
    pub parser_version: String,
    pub parsing_timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct FailedTool {
    pub name: String,
    pub command: String,
    pub error: String,
    pub exit_code: i32,
    pub suggested_fix: Option<String>,
}

pub struct ReportGenerator {
    target: String,
    start_time: DateTime<Utc>,
    output_dir: PathBuf,
    config_name: String,
    parser: crate::parser::GenericParser,
    template_engine: Option<crate::template::TemplateEngine>,
}

impl ReportGenerator {
    pub fn new(target: String, output_dir: PathBuf, config_name: String) -> Self {
        let templates_dir = std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("."))
            .join("templates");
        
        let template_engine = crate::template::TemplateEngine::new(templates_dir).ok();
        
        Self {
            target,
            start_time: Utc::now(),
            output_dir,
            config_name,
            parser: crate::parser::GenericParser::new(),
            template_engine,
        }
    }

    pub fn generate_summary_report(&self, results: &[ToolResult]) -> Result<ScanSummary, Box<dyn std::error::Error + Send + Sync>> {
        let end_time = Utc::now();
        let duration = end_time.signed_duration_since(self.start_time);

        let metadata = ScanMetadata {
            target: self.target.clone(),
            start_time: self.start_time,
            end_time,
            duration_seconds: duration.num_milliseconds() as f64 / 1000.0,
            output_directory: self.output_dir.to_string_lossy().to_string(),
            config_used: self.config_name.clone(),
        };

        let execution_stats = self.calculate_execution_stats(results)?;
        let tool_results = self.convert_tool_results(results)?;
        
        // Use generic parser to extract discoveries from all tool outputs
        let (discoveries, raw_outputs, parsing_metadata) = self.parse_all_outputs(results)?;
        
        let failed_tools = self.extract_failed_tools(results);

        Ok(ScanSummary {
            metadata,
            execution_stats,
            tool_results,
            discoveries,
            raw_outputs,
            parsing_metadata,
            failed_tools,
        })
    }

    // New multi-format templated report generation
    pub fn save_report(&mut self, summary: &ScanSummary, format: crate::template::OutputFormat) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
        let filename = format!("scan_summary.{}", format.extension());
        let report_path = self.output_dir.join(filename);
        
        let content = if let Some(ref mut engine) = self.template_engine {
            engine.render_summary(summary, format, None)?
        } else {
            // Fallback to basic JSON serialization if no template engine
            serde_json::to_string_pretty(summary)?
        };
        
        fs::write(&report_path, content)?;
        Ok(report_path)
    }

    // Legacy methods for backwards compatibility
    pub fn save_json_report(&mut self, summary: &ScanSummary) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
        self.save_report(summary, crate::template::OutputFormat::Json)
    }

    pub fn save_html_report(&mut self, summary: &ScanSummary) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
        self.save_report(summary, crate::template::OutputFormat::Html)
    }

    pub fn save_text_report(&mut self, summary: &ScanSummary) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
        self.save_report(summary, crate::template::OutputFormat::Text)
    }

    pub fn save_markdown_report(&mut self, summary: &ScanSummary) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
        self.save_report(summary, crate::template::OutputFormat::Markdown)
    }

    fn calculate_execution_stats(&self, results: &[ToolResult]) -> Result<ExecutionStats, Box<dyn std::error::Error + Send + Sync>> {
        let total_tools = results.len();
        let successful_tools = results.iter().filter(|r| r.exit_code == 0).count();
        let failed_tools = total_tools - successful_tools;
        let tools_with_output = results.iter().filter(|r| r.has_output).count();
        
        let mut total_output_size = 0u64;
        for result in results {
            if let Ok(metadata) = fs::metadata(&result.stdout_file) {
                total_output_size += metadata.len();
            }
        }

        Ok(ExecutionStats {
            total_tools,
            successful_tools,
            failed_tools,
            tools_with_output,
            total_output_size,
        })
    }

    fn convert_tool_results(&self, results: &[ToolResult]) -> Result<Vec<ToolResultSummary>, Box<dyn std::error::Error + Send + Sync>> {
        let mut summaries = Vec::new();

        for result in results {
            let output_size = fs::metadata(&result.stdout_file)
                .map(|m| m.len())
                .unwrap_or(0);

            summaries.push(ToolResultSummary {
                name: result.tool_name.clone(),
                command: "N/A".to_string(), // Command not stored in ToolResult
                exit_code: result.exit_code,
                duration_seconds: result.duration.as_secs_f64(),
                has_output: result.has_output,
                output_size,
                error_message: result.error.clone(),
            });
        }

        Ok(summaries)
    }

    fn parse_all_outputs(&self, results: &[ToolResult]) -> Result<(Vec<Discovery>, HashMap<String, RawToolOutput>, ParsingMetadata), Box<dyn std::error::Error + Send + Sync>> {
        let mut all_discoveries = Vec::new();
        let mut raw_outputs = HashMap::new();
        let mut total_lines = 0u64;
        let mut total_successful = 0u64;
        let mut total_failed = 0u64;
        let mut all_patterns = std::collections::HashSet::new();

        for result in results {
            // Read stdout content
            let stdout_content = fs::read_to_string(&result.stdout_file).unwrap_or_default();
            let stderr_content = fs::read_to_string(&result.stderr_file).unwrap_or_default();
            
            // Parse discoveries using generic parser
            let parse_result = self.parser.parse_output(&stdout_content, &result.tool_name);
            
            // Collect discoveries
            all_discoveries.extend(parse_result.discoveries);
            
            // Update parsing statistics
            total_lines += parse_result.metadata.total_lines_processed;
            total_successful += parse_result.metadata.successful_extractions;
            total_failed += parse_result.metadata.failed_extractions;
            for pattern in &parse_result.metadata.patterns_used {
                all_patterns.insert(pattern.clone());
            }
            
            // Store raw output
            let file_paths = vec![
                result.stdout_file.to_string_lossy().to_string(),
                result.stderr_file.to_string_lossy().to_string(),
            ];
            
            let parsing_errors = if parse_result.metadata.failed_extractions > 0 {
                vec![format!("Failed to parse {} lines", parse_result.metadata.failed_extractions)]
            } else {
                vec![]
            };
            
            raw_outputs.insert(result.tool_name.clone(), RawToolOutput {
                stdout: if stdout_content.len() > 10000 { 
                    format!("{}... (truncated from {} chars)", &stdout_content[..10000], stdout_content.len())
                } else {
                    stdout_content.clone()
                },
                stderr: stderr_content,
                file_paths,
                size_bytes: stdout_content.len() as u64,
                parsed_success: parse_result.metadata.failed_extractions == 0,
                parsing_errors,
            });
        }

        let parsing_metadata = ParsingMetadata {
            patterns_used: all_patterns.into_iter().collect(),
            total_lines_processed: total_lines,
            successful_extractions: total_successful,
            failed_extractions: total_failed,
            parser_version: "1.0.0".to_string(),
            parsing_timestamp: Utc::now(),
        };

        Ok((all_discoveries, raw_outputs, parsing_metadata))
    }

    fn extract_failed_tools(&self, results: &[ToolResult]) -> Vec<FailedTool> {
        results
            .iter()
            .filter(|r| r.exit_code != 0)
            .map(|r| FailedTool {
                name: r.tool_name.clone(),
                command: "N/A".to_string(), // Command not stored in ToolResult
                error: r.error.clone().unwrap_or_else(|| format!("Process exited with code {}", r.exit_code)),
                exit_code: r.exit_code,
                suggested_fix: self.suggest_fix_for_tool(&r.tool_name, r.exit_code),
            })
            .collect()
    }

    fn suggest_fix_for_tool(&self, tool_name: &str, exit_code: i32) -> Option<String> {
        match (tool_name, exit_code) {
            (name, 127) if name.contains("nmap") => Some("Install nmap: sudo apt install nmap (Ubuntu) or brew install nmap (macOS)".to_string()),
            (name, 127) if name.contains("naabu") => Some("Install naabu: go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest".to_string()),
            (name, 127) if name.contains("httpx") => Some("Install httpx: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest".to_string()),
            (name, 127) if name.contains("nuclei") => Some("Install nuclei: go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest".to_string()),
            (name, 127) if name.contains("gobuster") => Some("Install gobuster: go install github.com/OJ/gobuster/v3@latest".to_string()),
            (_, 127) => Some("Command not found. Make sure the tool is installed and in your PATH.".to_string()),
            (_, 1) => Some("Tool failed with error. Check tool-specific logs for details.".to_string()),
            (_, 2) => Some("Invalid command line arguments. Check tool syntax.".to_string()),
            _ => None,
        }
    }
}