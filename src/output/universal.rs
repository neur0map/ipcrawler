use crate::config::{Severity, Tool};
use crate::executor::runner::TaskResult;
use crate::llm::LLMClient;
use crate::output::parser::Finding;
use crate::output::regex_matcher::RegexMatcher;
use anyhow::Result;
use std::collections::HashSet;

/// Universal output processor - tool-agnostic parsing with optional LLM enhancement
pub struct UniversalProcessor {
    use_llm: bool,
}

impl UniversalProcessor {
    pub fn new(use_llm: bool) -> Self {
        Self { use_llm }
    }

    /// Process tool output universally - always preserves raw output
    pub async fn process(&self, tool_name: &str, result: &TaskResult) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();

        // Always create a base finding with complete raw output preservation
        let base_finding = Finding::new(
            tool_name.to_string(),
            result.target.clone(),
            result.port,
            Severity::Info,
            format!("{} execution", tool_name),
            self.generate_simple_summary(&result.stdout, &result.stderr),
            result.stdout.clone(),
            result.stderr.clone(),
            None, // LLM analysis will be added later if enabled
        );

        findings.push(base_finding);

        // If LLM is enabled, enhance with intelligent analysis
        if self.use_llm && !result.stdout.is_empty() {
            if let Ok(llm_analysis) = self
                .analyze_with_llm(tool_name, &result.stdout, &result.stderr)
                .await
            {
                // Add LLM-enhanced findings
                if let Ok(enhanced_findings) =
                    self.extract_llm_findings(tool_name, result, &llm_analysis)
                {
                    findings.extend(enhanced_findings);
                }

                // Update base finding with LLM analysis
                if let Some(base_finding) = findings.get_mut(0) {
                    base_finding.llm_analysis = Some(llm_analysis);
                }
            }
        }

        Ok(findings)
    }

    /// Process tool output with provided LLM client
    pub async fn process_with_llm(
        &self,
        tool: &Tool,
        result: &TaskResult,
        llm_client: Option<&LLMClient>,
    ) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();

        // First, apply YAML-defined regex patterns if they exist
        if let Some(patterns) = &tool.output.patterns {
            if !patterns.is_empty() {
                match RegexMatcher::match_patterns(
                    &tool.name,
                    &result.target,
                    result.port,
                    &result.stdout,
                    &result.stderr,
                    patterns,
                ) {
                    Ok(pattern_findings) => {
                        if !pattern_findings.is_empty() {
                            println!(
                                "✓ Pattern matcher found {} findings for {}",
                                pattern_findings.len(),
                                tool.name
                            );
                            findings.extend(pattern_findings);
                        }
                    }
                    Err(e) => {
                        eprintln!("Error applying patterns for {}: {}", tool.name, e);
                    }
                }
            }
        }

        // Always create a base finding with complete raw output preservation
        let base_finding = Finding::new(
            tool.name.clone(),
            result.target.clone(),
            result.port,
            Severity::Info,
            format!("{} execution", tool.name),
            self.generate_simple_summary(&result.stdout, &result.stderr),
            result.stdout.clone(),
            result.stderr.clone(),
            None, // LLM analysis will be added later if client is provided
        );

        findings.push(base_finding);

        // If LLM client is provided and output is not empty, enhance with intelligent analysis
        if let Some(client) = llm_client {
            if !result.stdout.is_empty() {
                // Create a context message for analysis
                let context = vec![
                    crate::llm::prompts::Message {
                        role: "system".to_string(),
                        content: "You are analyzing security reconnaissance tool outputs. Focus on security-relevant findings.".to_string(),
                    }
                ];

                // Use specialized analysis based on tool type
                let llm_analysis = if tool.name.contains("nmap") || tool.name.contains("masscan") {
                    client
                        .analyze_network_scan(&tool.name, &result.stdout)
                        .await
                } else if tool.name.contains("dig") || tool.name.contains("nslookup") {
                    client.analyze_dns_recon(&tool.name, &result.stdout).await
                } else if tool.name.contains("nikto") || tool.name.contains("nuclei") {
                    client
                        .analyze_vulnerability_scan(&tool.name, &result.stdout)
                        .await
                } else {
                    // Use context analysis for generic tools
                    client
                        .analyze_with_context(&tool.name, &result.stdout, &context)
                        .await
                };

                if let Ok(llm_analysis) = llm_analysis {
                    // Add LLM-enhanced findings
                    if let Ok(enhanced_findings) =
                        self.extract_llm_findings(&tool.name, result, &llm_analysis)
                    {
                        findings.extend(enhanced_findings);
                    }

                    // Update base finding with LLM analysis
                    if let Some(base_finding) = findings.get_mut(0) {
                        base_finding.llm_analysis = Some(llm_analysis);
                    }
                }
            }
        }

        Ok(findings)
    }

    /// Check if LLM is enabled for this processor
    pub fn is_llm_enabled(&self) -> bool {
        self.use_llm
    }

    /// Generate simple heuristic summary without LLM
    fn generate_simple_summary(&self, stdout: &str, stderr: &str) -> String {
        let mut summary_parts = Vec::new();

        // Count lines in output
        let stdout_lines = stdout.lines().count();
        let stderr_lines = stderr.lines().count();

        if stdout_lines > 0 {
            summary_parts.push(format!("{} lines of output", stdout_lines));
        }

        // Use ContentAnalyzer to check for errors
        if ContentAnalyzer::has_errors(stderr) {
            summary_parts.push(format!("{} lines of errors/warnings", stderr_lines));
        }

        // Use ContentAnalyzer for enhanced content detection
        if ContentAnalyzer::is_structured(stdout) {
            summary_parts.push("structured data".to_string());
        }

        // Extract ports using ContentAnalyzer
        let ports = ContentAnalyzer::extract_ports(stdout);
        if !ports.is_empty() {
            summary_parts.push("port scan results".to_string());
        }

        // Extract key lines for content analysis
        let key_lines = ContentAnalyzer::extract_key_lines(stdout);

        if key_lines
            .iter()
            .any(|line| line.contains("ssh") || line.contains("ftp") || line.contains("http"))
        {
            summary_parts.push("service detection".to_string());
        }

        if key_lines
            .iter()
            .any(|line| line.contains("vulnerab") || line.contains("CVE") || line.contains("risk"))
        {
            summary_parts.push("security findings".to_string());
        }

        if key_lines
            .iter()
            .any(|line| line.contains("A ") || line.contains("AAAA") || line.contains("MX"))
        {
            summary_parts.push("DNS records".to_string());
        }

        if summary_parts.is_empty() {
            "Tool execution completed".to_string()
        } else {
            summary_parts.join(", ")
        }
    }

    /// Analyze output with LLM (placeholder for now)
    async fn analyze_with_llm(
        &self,
        tool_name: &str,
        stdout: &str,
        _stderr: &str,
    ) -> Result<String> {
        // Enhanced analysis using ContentAnalyzer
        let ports = ContentAnalyzer::extract_ports(stdout);
        let has_errors = ContentAnalyzer::has_errors(_stderr);
        let is_structured = ContentAnalyzer::is_structured(stdout);
        let key_lines = ContentAnalyzer::extract_key_lines(stdout);

        let analysis = format!(
            "LLM analysis for {}:\n- Output size: {} chars\n- Lines: {}\n- Ports detected: {:?}\n- Has errors: {}\n- Structured data: {}\n- Key findings: {}",
            tool_name,
            stdout.len(),
            stdout.lines().count(),
            ports,
            has_errors,
            is_structured,
            key_lines.len()
        );
        Ok(analysis)
    }

    /// Extract structured findings from LLM analysis
    fn extract_llm_findings(
        &self,
        tool_name: &str,
        result: &TaskResult,
        llm_analysis: &str,
    ) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();

        // TODO: Parse structured LLM output
        // For now, create a simple enhanced finding
        if !llm_analysis.is_empty() {
            findings.push(Finding::new(
                tool_name.to_string(),
                result.target.clone(),
                result.port,
                Severity::Medium,
                "LLM Analysis".to_string(),
                "Intelligent analysis of tool output".to_string(),
                result.stdout.clone(),
                result.stderr.clone(),
                Some(llm_analysis.to_string()),
            ));
        }

        Ok(findings)
    }
}

/// Simple heuristics for identifying important content
pub struct ContentAnalyzer;

impl ContentAnalyzer {
    /// Extract potential ports from any text output
    pub fn extract_ports(text: &str) -> Vec<u16> {
        let mut ports = HashSet::new();

        // Compile regex patterns once outside the loop
        let port_tcp_udp = regex::Regex::new(r"(\d+)/(tcp|udp)").ok();
        let port_keyword = regex::Regex::new(r"[Pp]ort:?\s+(\d+)").ok();
        let port_colon = regex::Regex::new(r":(\d+)\b").ok();

        // Look for common port patterns
        for line in text.lines() {
            // Pattern: "22/tcp", "80/udp", etc.
            if let Some(re) = &port_tcp_udp {
                if let Some(caps) = re.captures(line) {
                    if let Ok(port) = caps[1].parse::<u16>() {
                        ports.insert(port);
                    }
                }
            }

            // Pattern: "Port: 22", "port 80", etc.
            if let Some(re) = &port_keyword {
                if let Some(caps) = re.captures(line) {
                    if let Ok(port) = caps[1].parse::<u16>() {
                        ports.insert(port);
                    }
                }
            }

            // Pattern: ":22" (but avoid false positives like times)
            if let Some(re) = &port_colon {
                if let Some(caps) = re.captures(line) {
                    if let Ok(port) = caps[1].parse::<u16>() {
                        if port > 0 {
                            ports.insert(port);
                        }
                    }
                }
            }
        }

        let mut result: Vec<u16> = ports.into_iter().collect();
        result.sort_unstable();
        result
    }

    /// Detect if output contains errors or warnings
    pub fn has_errors(stderr: &str) -> bool {
        !stderr.trim().is_empty()
            || stderr.to_lowercase().contains("error")
            || stderr.to_lowercase().contains("failed")
            || stderr.to_lowercase().contains("denied")
    }

    /// Detect if output looks like structured data (tables, JSON, etc.)
    pub fn is_structured(stdout: &str) -> bool {
        stdout.contains('|') && stdout.lines().count() >= 2
            || stdout.contains('\t') && stdout.lines().count() >= 2
            || stdout.trim_start().starts_with('{') && stdout.trim_end().ends_with('}')
            || stdout.trim_start().starts_with('<') && stdout.trim_end().ends_with('>')
    }

    /// Extract key information lines (non-empty, non-header lines)
    pub fn extract_key_lines(stdout: &str) -> Vec<String> {
        stdout
            .lines()
            .filter(|line| {
                let line = line.trim();
                !line.is_empty()
                    && !line.starts_with('#')
                    && !line.starts_with("Starting")
                    && !line.starts_with("Nmap done")
                    && !line.starts_with("---")
                    && line.len() > 3
            })
            .take(20) // Limit to first 20 relevant lines
            .map(|line| line.to_string())
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::executor::queue::TaskStatus;
    use std::time::Duration;

    #[tokio::test]
    async fn test_universal_processor_basic() {
        let processor = UniversalProcessor::new(false);

        let result = TaskResult {
            task_id: crate::executor::queue::TaskId::new("test", "target", None),
            tool_name: "test".to_string(),
            target: "127.0.0.1".to_string(),
            port: Some(80),
            actual_command: "test command".to_string(),
            status: TaskStatus::Completed {
                duration: Duration::from_secs(1),
                exit_code: 0,
            },
            stdout: "22/tcp open\n80/tcp open".to_string(),
            stderr: "".to_string(),
        };

        let findings = processor.process("nmap", &result).await.unwrap();
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].tool, "nmap");
        assert_eq!(findings[0].full_stdout, "22/tcp open\n80/tcp open");
    }

    #[test]
    fn test_content_analyzer_ports() {
        let text = "22/tcp open ssh\n80/tcp open http\nPort: 443\nFailed: 1234";
        let ports = ContentAnalyzer::extract_ports(text);
        assert_eq!(ports, vec![22, 80, 443]);
    }

    #[test]
    fn test_content_analyzer_structured() {
        assert!(ContentAnalyzer::is_structured(
            "PORT|STATE|SERVICE\n22|open|ssh"
        ));
        assert!(ContentAnalyzer::is_structured("{\"port\": 22}"));
        assert!(!ContentAnalyzer::is_structured("just plain text"));
    }
}
