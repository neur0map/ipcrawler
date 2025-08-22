use crate::output::{Discovery, DiscoveryType, ParsingMetadata};
use chrono::Utc;
use regex::Regex;
use serde_json::json;
use std::collections::HashMap;

pub struct GenericParser {
    patterns: Vec<ParsingPattern>,
    version: String,
}

#[derive(Debug, Clone)]
pub struct ParsingPattern {
    pub name: String,
    pub regex: Regex,
    pub discovery_type: String,
    pub confidence: f32,
    pub metadata_extractors: Vec<MetadataExtractor>,
}

#[derive(Debug, Clone)]
pub struct MetadataExtractor {
    pub key: String,
    pub group_index: usize,
    pub transform: Option<String>,
}

#[derive(Debug)]
pub struct ParseResult {
    pub discoveries: Vec<Discovery>,
    pub metadata: ParsingMetadata,
}

impl GenericParser {
    pub fn new() -> Self {
        Self {
            patterns: Self::load_default_patterns(),
            version: "1.0.0".to_string(),
        }
    }

    fn load_default_patterns() -> Vec<ParsingPattern> {
        vec![
            // Port discovery patterns (host:port format)
            ParsingPattern {
                name: "port_host_colon".to_string(),
                regex: Regex::new(r"([^:\s]+):(\d+)").unwrap(),
                discovery_type: "port".to_string(),
                confidence: 0.9,
                metadata_extractors: vec![
                    MetadataExtractor { key: "host".to_string(), group_index: 1, transform: None },
                    MetadataExtractor { key: "port".to_string(), group_index: 2, transform: None },
                ],
            },
            
            // Nmap service detection (80/tcp open http nginx)
            ParsingPattern {
                name: "nmap_service".to_string(),
                regex: Regex::new(r"(\d+)/(tcp|udp)\s+(\w+)\s+(\w+)(?:\s+(.+))?").unwrap(),
                discovery_type: "service".to_string(),
                confidence: 0.95,
                metadata_extractors: vec![
                    MetadataExtractor { key: "port".to_string(), group_index: 1, transform: None },
                    MetadataExtractor { key: "protocol".to_string(), group_index: 2, transform: None },
                    MetadataExtractor { key: "state".to_string(), group_index: 3, transform: None },
                    MetadataExtractor { key: "service".to_string(), group_index: 4, transform: None },
                    MetadataExtractor { key: "version".to_string(), group_index: 5, transform: None },
                ],
            },

            // Generic port/protocol pattern (80/tcp, 443/udp)
            ParsingPattern {
                name: "port_protocol".to_string(),
                regex: Regex::new(r"(\d+)/(tcp|udp)").unwrap(),
                discovery_type: "port".to_string(),
                confidence: 0.8,
                metadata_extractors: vec![
                    MetadataExtractor { key: "port".to_string(), group_index: 1, transform: None },
                    MetadataExtractor { key: "protocol".to_string(), group_index: 2, transform: None },
                ],
            },

            // HTTP status responses (200 OK, 404 Not Found)
            ParsingPattern {
                name: "http_status".to_string(),
                regex: Regex::new(r"HTTP/[\d.]+\s+(\d+)\s+([^\r\n]+)").unwrap(),
                discovery_type: "custom".to_string(),
                confidence: 0.7,
                metadata_extractors: vec![
                    MetadataExtractor { key: "status_code".to_string(), group_index: 1, transform: None },
                    MetadataExtractor { key: "status_text".to_string(), group_index: 2, transform: None },
                    MetadataExtractor { key: "category".to_string(), group_index: 0, transform: Some("http_response".to_string()) },
                ],
            },

            // Directory/file paths (/admin, /login, etc.)
            ParsingPattern {
                name: "directory_path".to_string(),
                regex: Regex::new(r"\s+(\d+)\s+(/.+?)(?:\s|$)").unwrap(),
                discovery_type: "directory".to_string(),
                confidence: 0.6,
                metadata_extractors: vec![
                    MetadataExtractor { key: "status".to_string(), group_index: 1, transform: None },
                    MetadataExtractor { key: "path".to_string(), group_index: 2, transform: None },
                ],
            },
        ]
    }

    pub fn parse_output(&self, content: &str, tool_name: &str) -> ParseResult {
        let mut discoveries = Vec::new();
        let mut total_lines = 0u64;
        let mut successful_extractions = 0u64;
        let mut failed_extractions = 0u64;
        let mut patterns_used = Vec::new();

        for line in content.lines() {
            total_lines += 1;
            
            for pattern in &self.patterns {
                if let Some(captures) = pattern.regex.captures(line) {
                    match self.create_discovery_from_pattern(pattern, &captures, tool_name, line) {
                        Ok(discovery) => {
                            discoveries.push(discovery);
                            successful_extractions += 1;
                            if !patterns_used.contains(&pattern.name) {
                                patterns_used.push(pattern.name.clone());
                            }
                        }
                        Err(_) => {
                            failed_extractions += 1;
                        }
                    }
                }
            }
        }

        let metadata = ParsingMetadata {
            patterns_used,
            total_lines_processed: total_lines,
            successful_extractions,
            failed_extractions,
            parser_version: self.version.clone(),
            parsing_timestamp: Utc::now(),
        };

        ParseResult { discoveries, metadata }
    }

    fn create_discovery_from_pattern(
        &self,
        pattern: &ParsingPattern,
        captures: &regex::Captures,
        tool_name: &str,
        original_line: &str,
    ) -> Result<Discovery, Box<dyn std::error::Error>> {
        let mut metadata = HashMap::new();
        
        // Extract metadata using the defined extractors
        for extractor in &pattern.metadata_extractors {
            if let Some(matched) = captures.get(extractor.group_index) {
                let value = if let Some(transform) = &extractor.transform {
                    json!(transform)
                } else {
                    json!(matched.as_str())
                };
                metadata.insert(extractor.key.clone(), value);
            }
        }

        // Create discovery type based on pattern
        let discovery_type = match pattern.discovery_type.as_str() {
            "port" => {
                let port_str = metadata.get("port").and_then(|v| v.as_str()).unwrap_or("0");
                let port: u16 = port_str.parse().unwrap_or(0);
                let protocol = metadata.get("protocol").and_then(|v| v.as_str()).unwrap_or("tcp").to_string();
                
                DiscoveryType::Port { number: port, protocol }
            }
            "service" => {
                let port_str = metadata.get("port").and_then(|v| v.as_str()).unwrap_or("0");
                let port: u16 = port_str.parse().unwrap_or(0);
                let protocol = metadata.get("protocol").and_then(|v| v.as_str()).unwrap_or("tcp").to_string();
                let name = metadata.get("service").and_then(|v| v.as_str()).unwrap_or("unknown").to_string();
                let version = metadata.get("version").and_then(|v| v.as_str()).map(|s| s.to_string());
                
                DiscoveryType::Service { port, protocol, name, version }
            }
            "directory" => {
                let path = metadata.get("path").and_then(|v| v.as_str()).unwrap_or("/").to_string();
                let status_str = metadata.get("status").and_then(|v| v.as_str()).unwrap_or("0");
                let status: u16 = status_str.parse().unwrap_or(0);
                
                DiscoveryType::Directory { path, status }
            }
            "custom" => {
                let category = metadata.get("category").and_then(|v| v.as_str()).unwrap_or("unknown").to_string();
                let subcategory = metadata.get("subcategory").and_then(|v| v.as_str()).map(|s| s.to_string());
                
                DiscoveryType::Custom { category, subcategory }
            }
            _ => {
                DiscoveryType::Custom { 
                    category: pattern.discovery_type.clone(),
                    subcategory: None 
                }
            }
        };

        // Create value string representation
        let value = match &discovery_type {
            DiscoveryType::Port { number, protocol } => format!("{}:{}", protocol, number),
            DiscoveryType::Service { port, protocol, name, .. } => format!("{}:{}/{}", name, port, protocol),
            DiscoveryType::Directory { path, status } => format!("{} ({})", path, status),
            DiscoveryType::Custom { category, .. } => category.clone(),
            _ => original_line.to_string(),
        };

        Ok(Discovery {
            discovery_type,
            value,
            confidence: pattern.confidence,
            metadata,
            detected_by: tool_name.to_string(),
            detection_pattern: pattern.name.clone(),
            timestamp: Utc::now(),
        })
    }

    pub fn add_pattern(&mut self, pattern: ParsingPattern) {
        self.patterns.push(pattern);
    }

    pub fn get_patterns(&self) -> &[ParsingPattern] {
        &self.patterns
    }
}

impl Default for GenericParser {
    fn default() -> Self {
        Self::new()
    }
}