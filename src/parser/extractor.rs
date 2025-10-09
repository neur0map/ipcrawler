use super::llm::LlmParser;
use super::consistency::ConsistencyChecker;
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

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
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
    consistency_checker: ConsistencyChecker,
}

impl EntityExtractor {
    pub fn new(llm_parser: Option<LlmParser>, consistency_passes: usize) -> Self {
        Self {
            llm_parser,
            consistency_checker: ConsistencyChecker::new(consistency_passes),
        }
    }

    pub async fn extract(&self, tool_name: &str, output: &str) -> Result<ExtractedEntities> {
        if let Some(parser) = &self.llm_parser {
            let validated = self
                .consistency_checker
                .parse_with_consistency(parser, tool_name, output)
                .await?;

            if !validated.warnings.is_empty() {
                warn!(
                    "Consistency warnings for '{}': {}",
                    tool_name,
                    validated.warnings.join("; ")
                );
            }

            debug!(
                "Extracted from '{}': {} IPs, {} domains, {} ports, {} vulnerabilities (consistency: {:.2}, passes: {}/{})",
                tool_name,
                validated.entities.ips.len(),
                validated.entities.domains.len(),
                validated.entities.ports.len(),
                validated.entities.vulnerabilities.len(),
                validated.consistency_score,
                validated.num_passes,
                self.consistency_checker.num_passes,
            );

            return Ok(validated.entities);
        }

        Ok(ExtractedEntities::default())
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
