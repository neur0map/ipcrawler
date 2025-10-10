use super::extractor::ExtractedEntities;
use crate::templates::models::RegexPattern;
use anyhow::Result;
use regex::Regex;
use tracing::debug;

pub struct RegexParser;

impl RegexParser {
    pub fn new() -> Self {
        Self
    }

    pub fn parse_output(
        &self,
        tool_name: &str,
        output: &str,
        patterns: &[RegexPattern],
    ) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        if patterns.is_empty() {
            return self.parse_with_builtin_patterns(tool_name, output);
        }

        for pattern_config in patterns {
            let re = Regex::new(&pattern_config.pattern)?;

            for line in output.lines() {
                if let Some(captures) = re.captures(line) {
                    let value = if captures.len() > 1 {
                        captures.get(1).map(|m| m.as_str()).unwrap_or("")
                    } else {
                        captures.get(0).map(|m| m.as_str()).unwrap_or("")
                    };

                    match pattern_config.extract_as.as_str() {
                        "url" => entities.urls.push(value.to_string()),
                        "domain" => entities.domains.push(value.to_string()),
                        "ip" => entities.ips.push(value.to_string()),
                        "finding" => entities.findings.push(value.to_string()),
                        _ => {}
                    }
                }
            }
        }

        entities.urls.sort();
        entities.urls.dedup();
        entities.domains.sort();
        entities.domains.dedup();
        entities.ips.sort();
        entities.ips.dedup();
        entities.findings.sort();
        entities.findings.dedup();

        debug!(
            "Regex parsed from '{}': {} URLs, {} domains, {} IPs, {} findings",
            tool_name,
            entities.urls.len(),
            entities.domains.len(),
            entities.ips.len(),
            entities.findings.len()
        );

        Ok(entities)
    }

    fn parse_with_builtin_patterns(
        &self,
        tool_name: &str,
        output: &str,
    ) -> Result<ExtractedEntities> {
        match tool_name {
            "gobuster" => self.parse_gobuster(output),
            "ffuf-directory" | "ffuf-vhost" | "ffuf-subdomain" | "ffuf-parameters" => {
                self.parse_ffuf(output)
            }
            "feroxbuster" => self.parse_feroxbuster(output),
            "dirb" => self.parse_dirb(output),
            "dirsearch" => self.parse_dirsearch(output),
            _ => {
                debug!(
                    "No built-in regex patterns for tool '{}', using generic URL extraction",
                    tool_name
                );
                self.parse_generic_urls(output)
            }
        }
    }

    fn parse_gobuster(&self, output: &str) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        // Gobuster format: /path (Status: 200) [Size: 1234]
        let re = Regex::new(r"^(/[^\s]+)\s+\(Status:\s+(\d+)\)")?;

        for line in output.lines() {
            if let Some(captures) = re.captures(line) {
                if let Some(path) = captures.get(1) {
                    entities.findings.push(format!(
                        "Directory/File found: {} (Status: {})",
                        path.as_str(),
                        captures.get(2).map(|m| m.as_str()).unwrap_or("unknown")
                    ));
                }
            }
        }

        entities.findings.sort();
        entities.findings.dedup();

        debug!("Gobuster parsed: {} findings", entities.findings.len());
        Ok(entities)
    }

    fn parse_ffuf(&self, output: &str) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        // FFUF output format varies, try to extract URLs and status codes
        let url_re = Regex::new(r"https?://[^\s]+")?;
        let status_re = Regex::new(r"\[Status:\s+(\d+),\s+Size:\s+(\d+)")?;

        for line in output.lines() {
            // Extract URLs
            if let Some(url_match) = url_re.find(line) {
                entities.urls.push(url_match.as_str().to_string());
            }

            // Extract findings with status codes
            if let Some(captures) = status_re.captures(line) {
                if let Some(status) = captures.get(1) {
                    entities.findings.push(format!(
                        "Response: Status {} (Size: {} bytes)",
                        status.as_str(),
                        captures.get(2).map(|m| m.as_str()).unwrap_or("unknown")
                    ));
                }
            }
        }

        entities.urls.sort();
        entities.urls.dedup();
        entities.findings.sort();
        entities.findings.dedup();

        debug!(
            "FFUF parsed: {} URLs, {} findings",
            entities.urls.len(),
            entities.findings.len()
        );
        Ok(entities)
    }

    fn parse_feroxbuster(&self, output: &str) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        // Feroxbuster format: 200 GET 1234l 5678w 91011c http://example.com/path
        let re = Regex::new(r"^(\d+)\s+\w+\s+\d+l\s+\d+w\s+\d+c\s+(https?://[^\s]+)")?;

        for line in output.lines() {
            if let Some(captures) = re.captures(line) {
                if let Some(url) = captures.get(2) {
                    entities.urls.push(url.as_str().to_string());
                    entities.findings.push(format!(
                        "URL found: {} (Status: {})",
                        url.as_str(),
                        captures.get(1).map(|m| m.as_str()).unwrap_or("unknown")
                    ));
                }
            }
        }

        entities.urls.sort();
        entities.urls.dedup();
        entities.findings.sort();
        entities.findings.dedup();

        debug!(
            "Feroxbuster parsed: {} URLs, {} findings",
            entities.urls.len(),
            entities.findings.len()
        );
        Ok(entities)
    }

    fn parse_dirb(&self, output: &str) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        // DIRB format: + http://example.com/path (CODE:200|SIZE:1234)
        let re = Regex::new(r"^\+\s+(https?://[^\s]+)\s+\(CODE:(\d+)")?;

        for line in output.lines() {
            if let Some(captures) = re.captures(line) {
                if let Some(url) = captures.get(1) {
                    entities.urls.push(url.as_str().to_string());
                    entities.findings.push(format!(
                        "Directory found: {} (Code: {})",
                        url.as_str(),
                        captures.get(2).map(|m| m.as_str()).unwrap_or("unknown")
                    ));
                }
            }
        }

        entities.urls.sort();
        entities.urls.dedup();
        entities.findings.sort();
        entities.findings.dedup();

        debug!(
            "DIRB parsed: {} URLs, {} findings",
            entities.urls.len(),
            entities.findings.len()
        );
        Ok(entities)
    }

    fn parse_dirsearch(&self, output: &str) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        // Dirsearch format: [12:34:56] 200 - 1234B - /path
        let re = Regex::new(r"\[\d+:\d+:\d+\]\s+(\d+)\s+-\s+\d+[KMB]?\s+-\s+(/[^\s]+)")?;

        for line in output.lines() {
            if let Some(captures) = re.captures(line) {
                if let Some(path) = captures.get(2) {
                    entities.findings.push(format!(
                        "Path found: {} (Status: {})",
                        path.as_str(),
                        captures.get(1).map(|m| m.as_str()).unwrap_or("unknown")
                    ));
                }
            }
        }

        entities.findings.sort();
        entities.findings.dedup();

        debug!("Dirsearch parsed: {} findings", entities.findings.len());
        Ok(entities)
    }

    fn parse_generic_urls(&self, output: &str) -> Result<ExtractedEntities> {
        let mut entities = ExtractedEntities::default();

        // Generic URL extraction
        let url_re = Regex::new(r"https?://[^\s]+")?;

        for url_match in url_re.find_iter(output) {
            entities.urls.push(url_match.as_str().to_string());
        }

        entities.urls.sort();
        entities.urls.dedup();

        debug!("Generic URL extraction: {} found", entities.urls.len());
        Ok(entities)
    }
}
