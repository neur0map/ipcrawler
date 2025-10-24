use crate::config::{Severity, Tool};
use crate::executor::runner::TaskResult;
use crate::llm::LLMClient;
use crate::output::universal::UniversalProcessor;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Finding {
    pub tool: String,
    pub target: String,
    pub port: Option<u16>,
    pub severity: Severity,
    pub title: String,
    pub description: String,
    pub full_stdout: String,
    pub full_stderr: String,
    pub llm_analysis: Option<String>,
}

impl Finding {
    /// Create a new Finding instance
    ///
    /// This constructor has many arguments because it directly maps to all struct fields.
    /// For complex construction scenarios, consider using the struct directly with named fields.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        tool: String,
        target: String,
        port: Option<u16>,
        severity: Severity,
        title: String,
        description: String,
        full_stdout: String,
        full_stderr: String,
        llm_analysis: Option<String>,
    ) -> Self {
        Self {
            tool,
            target,
            port,
            severity,
            title,
            description,
            full_stdout,
            full_stderr,
            llm_analysis,
        }
    }

    pub fn dedup_key(&self) -> String {
        format!(
            "{}:{}:{}:{}",
            self.target,
            self.port.map_or("none".to_string(), |p| p.to_string()),
            self.severity.as_str(),
            self.title
        )
    }
}

pub struct OutputParser;

impl OutputParser {
    pub async fn parse(tool: &Tool, result: &TaskResult, use_llm: bool) -> Result<Vec<Finding>> {
        let processor = UniversalProcessor::new(use_llm);

        // Use the process method and log if LLM is enabled
        if processor.is_llm_enabled() {
            println!("Processing {} with LLM enhancement enabled", tool.name);
        }

        processor.process(&tool.name, result).await
    }

    /// Parse tool output using the universal processor with LLM client
    pub async fn parse_with_llm(
        tool: &Tool,
        result: &TaskResult,
        llm_client: Option<&LLMClient>,
    ) -> Result<Vec<Finding>> {
        let processor = UniversalProcessor::new(llm_client.is_some());
        processor.process_with_llm(tool, result, llm_client).await
    }

    // Legacy method for backward compatibility - used in dry-run mode
    pub fn parse_sync(tool: &Tool, result: &TaskResult) -> Result<Vec<Finding>> {
        let processor = UniversalProcessor::new(false);
        // Use tokio::task::block_in_place for async in sync context
        tokio::task::block_in_place(|| {
            tokio::runtime::Handle::current().block_on(processor.process(&tool.name, result))
        })
    }

    pub fn deduplicate(findings: Vec<Finding>) -> Vec<Finding> {
        let mut seen = HashSet::new();
        let mut deduplicated = Vec::new();

        for finding in findings {
            let key = finding.dedup_key();

            // Skip duplicate SSH hostkey findings from script_result pattern
            // Keep only the specific ssh_hostkey pattern findings
            if finding.title == "script_result" && finding.description.contains("ssh-hostkey") {
                continue;
            }

            // Skip duplicate "Non-web port skipped" findings - keep only one
            if finding.title == "Non-web port skipped" {
                if seen.contains("non_web_port_skipped") {
                    continue;
                } else {
                    seen.insert("non_web_port_skipped".to_string());
                }
            }

            // For security headers findings, consolidate by title and description pattern
            if finding.title.contains("Missing security headers") {
                let consolidated_key = format!("security_headers:{}", finding.description);
                if seen.contains(&consolidated_key) {
                    continue;
                } else {
                    seen.insert(consolidated_key);
                }
            }

            if seen.insert(key) {
                deduplicated.push(finding);
            }
        }

        deduplicated
    }

    pub fn sort_by_severity(findings: &mut [Finding]) {
        findings.sort_by(|a, b| {
            b.severity
                .cmp(&a.severity)
                .then_with(|| a.target.cmp(&b.target))
                .then_with(|| a.port.cmp(&b.port))
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deduplication() {
        let finding1 = Finding::new(
            "nmap".to_string(),
            "192.168.1.1".to_string(),
            Some(80),
            Severity::High,
            "Open port".to_string(),
            "Port 80 is open".to_string(),
            "raw".to_string(),
            "".to_string(),
            None,
        );

        let finding2 = finding1.clone();

        let findings = vec![finding1, finding2];
        let dedup = OutputParser::deduplicate(findings);

        assert_eq!(dedup.len(), 1);
    }

    #[test]
    fn test_sorting() {
        let mut findings = vec![
            Finding::new(
                "tool".to_string(),
                "192.168.1.1".to_string(),
                Some(80),
                Severity::Low,
                "test".to_string(),
                "desc".to_string(),
                "raw".to_string(),
                "".to_string(),
                None,
            ),
            Finding::new(
                "tool".to_string(),
                "192.168.1.1".to_string(),
                Some(443),
                Severity::Critical,
                "test".to_string(),
                "desc".to_string(),
                "raw".to_string(),
                "".to_string(),
                None,
            ),
        ];

        OutputParser::sort_by_severity(&mut findings);

        assert_eq!(findings[0].severity, Severity::Critical);
        assert_eq!(findings[1].severity, Severity::Low);
    }
}
