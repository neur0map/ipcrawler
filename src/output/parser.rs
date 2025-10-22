use crate::config::{OutputType, Pattern, Severity, Tool};
use crate::executor::runner::TaskResult;
use anyhow::Result;
use regex::Regex;
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
    pub raw_output: String,
}

impl Finding {
    pub fn new(
        tool: String,
        target: String,
        port: Option<u16>,
        severity: Severity,
        title: String,
        description: String,
        raw_output: String,
    ) -> Self {
        Self {
            tool,
            target,
            port,
            severity,
            title,
            description,
            raw_output,
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
    pub fn parse(tool: &Tool, result: &TaskResult) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();

        match tool.output.output_type {
            OutputType::Json => {
                if let Some(json_findings) = Self::parse_json(&result.stdout, tool, result)? {
                    findings.extend(json_findings);
                }
            }
            OutputType::Regex => {
                findings.extend(Self::parse_with_regex(&result.stdout, tool, result)?);
            }
            OutputType::Xml => {
                findings.extend(Self::parse_with_regex(&result.stdout, tool, result)?);
            }
        }

        if findings.is_empty() && !result.stdout.is_empty() {
            findings.push(Finding::new(
                result.tool_name.clone(),
                result.target.clone(),
                result.port,
                Severity::Info,
                "Tool output".to_string(),
                "Raw output from tool execution".to_string(),
                result.stdout.clone(),
            ));
        }

        Ok(findings)
    }

    fn parse_json(output: &str, tool: &Tool, result: &TaskResult) -> Result<Option<Vec<Finding>>> {
        if output.trim().is_empty() {
            return Ok(None);
        }

        match serde_json::from_str::<serde_json::Value>(output) {
            Ok(_json_value) => {
                let finding = Finding::new(
                    result.tool_name.clone(),
                    result.target.clone(),
                    result.port,
                    Severity::Info,
                    format!("{} scan results", tool.name),
                    "JSON output from tool".to_string(),
                    output.to_string(),
                );
                Ok(Some(vec![finding]))
            }
            Err(_) => Ok(Some(Self::parse_with_regex(output, tool, result)?)),
        }
    }

    fn parse_with_regex(output: &str, tool: &Tool, result: &TaskResult) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();

        for pattern in &tool.output.patterns {
            findings.extend(Self::apply_pattern(pattern, output, result)?);
        }

        Ok(findings)
    }

    fn apply_pattern(pattern: &Pattern, output: &str, result: &TaskResult) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();
        let regex = Regex::new(&pattern.regex)?;

        for captures in regex.captures_iter(output) {
            let matched_text = captures.get(0).map_or("", |m| m.as_str());

            let description = if captures.len() > 1 {
                captures
                    .iter()
                    .skip(1)
                    .filter_map(|c| c.map(|m| m.as_str()))
                    .collect::<Vec<_>>()
                    .join(" | ")
            } else {
                matched_text.to_string()
            };

            let finding = Finding::new(
                result.tool_name.clone(),
                result.target.clone(),
                result.port,
                pattern.severity,
                pattern.name.clone(),
                description,
                matched_text.to_string(),
            );

            findings.push(finding);
        }

        Ok(findings)
    }

    pub fn deduplicate(findings: Vec<Finding>) -> Vec<Finding> {
        let mut seen = HashSet::new();
        let mut deduplicated = Vec::new();

        for finding in findings {
            let key = finding.dedup_key();
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
            ),
            Finding::new(
                "tool".to_string(),
                "192.168.1.1".to_string(),
                Some(443),
                Severity::Critical,
                "test".to_string(),
                "desc".to_string(),
                "raw".to_string(),
            ),
        ];

        OutputParser::sort_by_severity(&mut findings);

        assert_eq!(findings[0].severity, Severity::Critical);
        assert_eq!(findings[1].severity, Severity::Low);
    }
}
