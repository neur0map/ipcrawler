use crate::config::{Pattern, Severity};
use crate::output::parser::Finding;
use anyhow::Result;
use regex::Regex;

pub struct RegexMatcher;

impl RegexMatcher {
    /// Apply YAML-defined regex patterns to tool output and extract findings
    pub fn match_patterns(
        tool_name: &str,
        target: &str,
        port: Option<u16>,
        stdout: &str,
        stderr: &str,
        patterns: &[Pattern],
    ) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();

        for pattern in patterns {
            // Compile the regex pattern
            let re = match Regex::new(&pattern.regex) {
                Ok(r) => r,
                Err(e) => {
                    eprintln!(
                        "Failed to compile regex for pattern '{}': {}",
                        pattern.name, e
                    );
                    continue;
                }
            };

            // Find all matches in the output
            for cap in re.captures_iter(stdout) {
                let matched_text = cap.get(0).map_or("", |m| m.as_str()).to_string();

                // Extract all capture groups
                let captures: Vec<String> = cap
                    .iter()
                    .skip(1) // Skip the full match (group 0)
                    .filter_map(|m| m.map(|m| m.as_str().to_string()))
                    .collect();

                // Extract port from capture group if specified
                let extracted_port = if let Some(port_idx) = pattern.port_capture {
                    if port_idx > 0 && (port_idx as usize) <= captures.len() {
                        captures
                            .get((port_idx - 1) as usize)
                            .and_then(|s| s.parse::<u16>().ok())
                    } else {
                        None
                    }
                } else {
                    port // Use the port from task context
                };

                // Build description from captures
                let description = if captures.is_empty() {
                    matched_text.clone()
                } else {
                    format!("{} | Captures: {}", matched_text, captures.join(", "))
                };

                // Parse severity from pattern
                let severity = Self::parse_severity(&pattern.severity);

                // Create finding
                let finding = Finding::new(
                    tool_name.to_string(),
                    target.to_string(),
                    extracted_port,
                    severity,
                    pattern.name.clone(),
                    description,
                    stdout.to_string(),
                    stderr.to_string(),
                    None, // No LLM analysis for pattern-based findings
                );

                findings.push(finding);
            }
        }

        Ok(findings)
    }

    /// Parse severity string from YAML into Severity enum
    fn parse_severity(severity_str: &str) -> Severity {
        match severity_str.to_lowercase().as_str() {
            "info" => Severity::Info,
            "low" => Severity::Low,
            "medium" => Severity::Medium,
            "high" => Severity::High,
            "critical" => Severity::Critical,
            _ => {
                eprintln!(
                    "Unknown severity level '{}', defaulting to Info",
                    severity_str
                );
                Severity::Info
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_regex_matcher_basic() {
        let patterns = vec![Pattern {
            name: "open_port".to_string(),
            regex: r"(\d+)/(tcp|udp)\s+open\s+([^\s]+)".to_string(),
            severity: "info".to_string(),
            port_capture: Some(1),
        }];

        let stdout = "22/tcp open ssh\n80/tcp open http\n443/tcp open https";
        let findings =
            RegexMatcher::match_patterns("nmap", "192.168.1.1", None, stdout, "", &patterns)
                .unwrap();

        assert_eq!(findings.len(), 3);
        assert_eq!(findings[0].port, Some(22));
        assert_eq!(findings[1].port, Some(80));
        assert_eq!(findings[2].port, Some(443));
    }

    #[test]
    fn test_severity_parsing() {
        assert_eq!(RegexMatcher::parse_severity("info"), Severity::Info);
        assert_eq!(RegexMatcher::parse_severity("low"), Severity::Low);
        assert_eq!(RegexMatcher::parse_severity("medium"), Severity::Medium);
        assert_eq!(RegexMatcher::parse_severity("high"), Severity::High);
        assert_eq!(RegexMatcher::parse_severity("critical"), Severity::Critical);
        assert_eq!(RegexMatcher::parse_severity("unknown"), Severity::Info);
    }

    #[test]
    fn test_multiple_patterns() {
        let patterns = vec![
            Pattern {
                name: "open_port".to_string(),
                regex: r"(\d+)/tcp\s+open".to_string(),
                severity: "info".to_string(),
                port_capture: Some(1),
            },
            Pattern {
                name: "hostname".to_string(),
                regex: r"Nmap scan report for ([^\s]+)".to_string(),
                severity: "info".to_string(),
                port_capture: None,
            },
        ];

        let stdout = "Nmap scan report for example.com\n22/tcp open ssh";
        let findings =
            RegexMatcher::match_patterns("nmap", "192.168.1.1", None, stdout, "", &patterns)
                .unwrap();

        // Should match both patterns
        assert!(findings.len() >= 2);
        assert!(findings.iter().any(|f| f.title == "hostname"));
        assert!(findings.iter().any(|f| f.title == "open_port"));
    }
}
