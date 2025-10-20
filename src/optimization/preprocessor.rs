use regex::Regex;
use std::collections::HashSet;
use super::tokens::{TokenManager};

#[derive(Clone)]
pub struct OutputPreprocessor {
    nmap_header_regex: Regex,
    dig_header_regex: Regex,
    whois_header_regex: Regex,
    traceroute_header_regex: Regex,
    empty_line_regex: Regex,
    whitespace_regex: Regex,
    token_manager: TokenManager,
}

impl OutputPreprocessor {
    pub fn new() -> Self {
        Self {
            nmap_header_regex: Regex::new(r"(?m)^Starting Nmap.*\n.*\n.*\n").unwrap(),
            dig_header_regex: Regex::new(r"(?m)^; <<>> DiG.*\n;; global options:.*\n").unwrap(),
            whois_header_regex: Regex::new(r"(?m)^%.*whois.*\n").unwrap(),
            traceroute_header_regex: Regex::new(r"(?m)^traceroute to.*\n").unwrap(),
            empty_line_regex: Regex::new(r"(?m)^\s*\n").unwrap(),
            whitespace_regex: Regex::new(r"[ \t]+").unwrap(),
            token_manager: TokenManager::new(),
        }
    }

    pub fn optimize_for_llm(&self, raw_output: &str, tool_name: &str) -> String {
        let mut optimized = raw_output.to_string();
        
        // 1. Remove tool-specific headers and footers
        optimized = self.strip_headers(optimized, tool_name);
        
        // 2. Remove empty lines and normalize whitespace
        optimized = self.normalize_whitespace(optimized);
        
        // 3. Remove duplicate consecutive lines
        optimized = self.deduplicate_lines(optimized);
        
        // 4. Smart truncation for very large outputs
        optimized = self.smart_truncate(optimized);
        
        // 5. Final cleanup
        optimized = self.final_cleanup(optimized);
        
        optimized.trim().to_string()
    }

    pub fn optimize_for_llm_with_token_limit(&self, raw_output: &str, tool_name: &str, token_limit: usize) -> String {
        let optimized = self.optimize_for_llm(raw_output, tool_name);
        
        // Apply token limit optimization if needed
        self.token_manager.optimize_for_token_limit(&optimized, token_limit, "english")
    }

    fn strip_headers(&self, output: String, tool_name: &str) -> String {
        let mut result = output;
        
        match tool_name.to_lowercase().as_str() {
            "nmap" => {
                result = self.nmap_header_regex.replace(&result, "").to_string();
                // Remove Nmap footer
                result = Regex::new(r"(?m)^Nmap done.*\n").unwrap()
                    .replace(&result, "").to_string();
            }
            "dig" => {
                result = self.dig_header_regex.replace(&result, "").to_string();
                // Remove DIG footer
                result = Regex::new(r"(?m)^;; Query time:.*\n;; SERVER:.*\n;; WHEN:.*\n;; MSG SIZE.*\n").unwrap()
                    .replace(&result, "").to_string();
            }
            "whois" => {
                result = self.whois_header_regex.replace(&result, "").to_string();
                // Remove WHOIS disclaimer lines
                result = Regex::new(r"(?m)^%.*\n").unwrap()
                    .replace(&result, "").to_string();
            }
            "traceroute" => {
                result = self.traceroute_header_regex.replace(&result, "").to_string();
            }
            _ => {
                // Generic header removal - look for common patterns
                result = Regex::new(r"(?m)^[#-]{3,}.*\n").unwrap()
                    .replace(&result, "").to_string();
            }
        }
        
        result
    }

    fn normalize_whitespace(&self, output: String) -> String {
        // Remove empty lines
        let result = self.empty_line_regex.replace_all(&output, "");
        
        // Normalize multiple spaces to single space
        self.whitespace_regex.replace_all(&result, " ").to_string()
    }

    fn deduplicate_lines(&self, output: String) -> String {
        let lines: Vec<&str> = output.lines().collect();
        let mut seen = HashSet::new();
        let mut deduped = Vec::new();
        
        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            
            if !seen.contains(trimmed) {
                seen.insert(trimmed);
                deduped.push(line);
            }
        }
        
        deduped.join("\n")
    }

    fn smart_truncate(&self, output: String) -> String {
        const MAX_LENGTH: usize = 4000; // Conservative limit for LLM input
        
        if output.len() <= MAX_LENGTH {
            return output;
        }
        
        let lines: Vec<&str> = output.lines().collect();
        
        // If we have many lines, try to keep the most important ones
        if lines.len() > 100 {
            // Keep first 50 lines and last 50 lines
            let first_part: Vec<&str> = lines.iter().take(50).cloned().collect();
            let last_part: Vec<&str> = lines.iter().skip(lines.len() - 50).cloned().collect();
            
            let mut result = first_part.join("\n");
            result.push_str("\n...[truncated]...\n");
            result.push_str(&last_part.join("\n"));
            
            // If still too long, truncate further
            if result.len() > MAX_LENGTH {
                return self.simple_truncate(&result, MAX_LENGTH);
            }
            
            result
        } else {
            self.simple_truncate(&output, MAX_LENGTH)
        }
    }

    fn simple_truncate(&self, output: &str, max_length: usize) -> String {
        if output.len() <= max_length {
            return output.to_string();
        }
        
        // Try to truncate at a line boundary
        let truncated = &output[..max_length];
        if let Some(last_newline) = truncated.rfind('\n') {
            format!("{}...[truncated]", &truncated[..last_newline])
        } else {
            format!("{}...[truncated]", &truncated[..max_length.saturating_sub(20)])
        }
    }

    fn final_cleanup(&self, output: String) -> String {
        // Remove any remaining multiple consecutive newlines
        Regex::new(r"\n{3,}").unwrap()
            .replace_all(&output, "\n\n")
            .to_string()
    }

    pub fn should_use_llm(&self, output: &str, tool_name: &str) -> bool {
        // Skip LLM for very small outputs
        if output.len() < 50 {
            return false;
        }
        
        // Skip LLM for simple success/failure outputs
        let simple_patterns = [
            r"^(Connection refused|Connection timed out|Host unreachable)",
            r"^(0 packets received|100% packet loss)",
            r"^(No answer|No response)",
            r"^(Command not found|not found)",
        ];
        
        for pattern in &simple_patterns {
            if Regex::new(pattern).unwrap().is_match(output.trim()) {
                return false;
            }
        }
        
        // Use heuristics to determine if LLM parsing would be beneficial
        self.contains_structured_data(output, tool_name)
    }

    fn contains_structured_data(&self, output: &str, tool_name: &str) -> bool {
        match tool_name.to_lowercase().as_str() {
            "nmap" => {
                // Look for port information
                Regex::new(r"\d+/(tcp|udp)\s+(open|closed|filtered)").unwrap()
                    .is_match(output)
            }
            "dig" => {
                // Look for DNS records
                Regex::new(r"(A|AAAA|CNAME|MX|NS|TXT|SOA)\s+").unwrap()
                    .is_match(output)
            }
            "whois" => {
                // Look for whois data patterns
                Regex::new(r"(Registrar|Created|Expires|Name Server|DNSSEC)").unwrap()
                    .is_match(output)
            }
            "ping" => {
                // Look for ping statistics
                Regex::new(r"(packets transmitted|received|packet loss|round-trip)").unwrap()
                    .is_match(output)
            }
            _ => {
                // Generic check for structured data
                // Look for lines with key-value patterns or tabular data
                let lines: Vec<&str> = output.lines().collect();
                if lines.len() < 3 {
                    return false;
                }
                
                // Check if multiple lines contain structured patterns
                let structured_lines = lines.iter()
                    .filter(|line| {
                        Regex::new(r"[:=]\s+|\s{2,}").unwrap().is_match(line)
                    })
                    .count();
                
                structured_lines >= 2
            }
        }
    }

    pub fn estimate_token_savings(&self, raw_output: &str, tool_name: &str) -> f32 {
        let original_tokens = self.estimate_tokens(raw_output);
        let optimized = self.optimize_for_llm(raw_output, tool_name);
        let optimized_tokens = self.estimate_tokens(&optimized);
        
        if original_tokens == 0 {
            0.0
        } else {
            1.0 - (optimized_tokens as f32 / original_tokens as f32)
        }
    }

    fn estimate_tokens(&self, text: &str) -> usize {
        // Rough estimation: ~4 characters per token for English text
        // This is a conservative estimate
        (text.len() / 4) + 10 // Add small buffer
    }
}

impl Default for OutputPreprocessor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nmap_preprocessing() {
        let preprocessor = OutputPreprocessor::new();
        let nmap_output = r#"
Starting Nmap 7.80 ( https://nmap.org ) at 2023-01-01 12:00 EST
Nmap scan report for example.com (93.184.216.34)
Host is up (0.016s latency).
Not shown: 998 closed ports
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.4 (protocol 2.0)
80/tcp open  http    Apache httpd 2.4.41
Nmap done: 1 IP address (1 host up) scanned in 0.45 seconds
        "#;

        let optimized = preprocessor.optimize_for_llm(nmap_output, "nmap");
        
        assert!(!optimized.contains("Starting Nmap"));
        assert!(!optimized.contains("Nmap done"));
        assert!(optimized.contains("22/tcp open"));
        assert!(optimized.contains("80/tcp open"));
    }

    #[test]
    fn test_deduplication() {
        let preprocessor = OutputPreprocessor::new();
        let output = "Line 1\nLine 2\nLine 2\nLine 2\nLine 3";
        
        let optimized = preprocessor.optimize_for_llm(output, "test");
        
        assert_eq!(optimized.lines().count(), 3);
        assert!(optimized.contains("Line 1"));
        assert!(optimized.contains("Line 2"));
        assert!(optimized.contains("Line 3"));
    }

    #[test]
    fn test_should_use_llm() {
        let preprocessor = OutputPreprocessor::new();
        
        // Simple output - should not use LLM
        assert!(!preprocessor.should_use_llm("Connection refused", "ping"));
        
        // Complex output - should use LLM
        let nmap_output = "22/tcp open  ssh\n80/tcp open  http\n443/tcp open  https";
        assert!(preprocessor.should_use_llm(nmap_output, "nmap"));
    }
}