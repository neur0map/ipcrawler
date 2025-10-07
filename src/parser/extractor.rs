use super::llm::LlmParser;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use tracing::{debug, warn};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ExtractedEntities {
    pub ips: Vec<String>,
    pub domains: Vec<String>,
    pub urls: Vec<String>,
    pub ports: Vec<PortInfo>,
    pub vulnerabilities: Vec<Vulnerability>,
    pub findings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortInfo {
    pub port: u16,
    pub protocol: String,
    pub service: Option<String>,
    pub version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vulnerability {
    pub name: String,
    pub severity: String,
    pub description: String,
}

pub struct EntityExtractor {
    llm_parser: Option<LlmParser>,
}

impl EntityExtractor {
    pub fn new(llm_parser: Option<LlmParser>) -> Self {
        Self { llm_parser }
    }

    pub async fn extract(&self, tool_name: &str, output: &str) -> Result<ExtractedEntities> {
        if let Some(parser) = &self.llm_parser {
            match parser.parse_output(tool_name, output).await {
                Ok(json_response) => {
                    debug!("LLM response length: {} bytes", json_response.len());

                    let cleaned = self.extract_json(&json_response);

                    match serde_json::from_str::<ExtractedEntities>(&cleaned) {
                        Ok(entities) => return Ok(entities),
                        Err(e) => {
                            warn!(
                                "Failed to parse LLM JSON response: {}. Response: {}",
                                e,
                                &cleaned[..cleaned.len().min(500)]
                            );
                            return Ok(ExtractedEntities::default());
                        }
                    }
                }
                Err(e) => {
                    warn!("LLM parsing failed for '{}': {}", tool_name, e);
                }
            }
        }

        Ok(ExtractedEntities::default())
    }

    fn extract_json(&self, text: &str) -> String {
        if let Some(start) = text.find('{') {
            if let Some(end) = text.rfind('}') {
                if end > start {
                    return text[start..=end].to_string();
                }
            }
        }

        if let Some(start) = text.find("```json") {
            let content = &text[start + 7..];
            if let Some(end) = content.find("```") {
                return content[..end].trim().to_string();
            }
        }

        text.trim().to_string()
    }

    pub fn merge_entities(&self, all_entities: Vec<ExtractedEntities>) -> ExtractedEntities {
        let mut merged = ExtractedEntities::default();

        for entities in all_entities {
            merged.ips.extend(entities.ips);
            merged.domains.extend(entities.domains);
            merged.urls.extend(entities.urls);
            merged.ports.extend(entities.ports);
            merged.vulnerabilities.extend(entities.vulnerabilities);
            merged.findings.extend(entities.findings);
        }

        merged.ips.sort();
        merged.ips.dedup();
        merged.domains.sort();
        merged.domains.dedup();
        merged.urls.sort();
        merged.urls.dedup();
        merged.findings.sort();
        merged.findings.dedup();

        merged
    }
}
