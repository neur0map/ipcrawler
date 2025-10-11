use super::extractor::ExtractedEntities;
use super::llm::LlmParser;
use super::retry::RetryStrategy;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use tracing::{info, warn};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidatedEntities {
    pub entities: ExtractedEntities,
    pub consistency_score: f64,
    pub warnings: Vec<String>,
    pub num_passes: usize,
}

pub struct ConsistencyChecker {
    pub num_passes: usize,
    verbose: bool,
}

impl ConsistencyChecker {
    pub fn new(num_passes: usize, verbose: bool) -> Self {
        Self {
            num_passes: num_passes.max(1),
            verbose,
        }
    }

    pub async fn parse_with_consistency(
        &self,
        llm: &LlmParser,
        tool_name: &str,
        output: &str,
    ) -> Result<ValidatedEntities> {
        if output.trim().is_empty() {
            return Ok(ValidatedEntities {
                entities: ExtractedEntities::default(),
                consistency_score: 1.0,
                warnings: vec![],
                num_passes: 0,
            });
        }

        if self.verbose {
            info!(
                "Running {} consistency passes for '{}'",
                self.num_passes, tool_name
            );
        }

        let mut all_passes = Vec::new();
        let mut errors = Vec::new();

        let retry_strategy = RetryStrategy::new(3);

        for pass_num in 1..=self.num_passes {
            // Wrap each pass in retry logic
            let result = retry_strategy
                .retry_with_backoff(|| self.parse_single_pass(llm, tool_name, output, pass_num))
                .await;

            match result {
                Ok(entities) => all_passes.push(entities),
                Err(e) => {
                    if self.verbose {
                        warn!(
                            "Pass {}/{} failed after retries: {}",
                            pass_num, self.num_passes, e
                        );
                    }
                    errors.push(format!("Pass {} failed: {}", pass_num, e));
                }
            }
        }

        if all_passes.is_empty() {
            return Ok(ValidatedEntities {
                entities: ExtractedEntities::default(),
                consistency_score: 0.0,
                warnings: errors,
                num_passes: 0,
            });
        }

        let merged = self.merge_with_union(&all_passes);
        let consistency = self.calculate_consistency(&all_passes);
        let mut warnings = self.generate_warnings(consistency, &all_passes);
        warnings.extend(errors);

        if self.verbose {
            info!(
                "Consistency check complete: {}/{} passes succeeded, score: {:.2}",
                all_passes.len(),
                self.num_passes,
                consistency
            );
        }

        Ok(ValidatedEntities {
            entities: merged,
            consistency_score: consistency,
            warnings,
            num_passes: all_passes.len(),
        })
    }

    async fn parse_single_pass(
        &self,
        llm: &LlmParser,
        tool_name: &str,
        output: &str,
        pass_num: usize,
    ) -> Result<ExtractedEntities> {
        let json_response = llm.parse_output(tool_name, output).await?;
        let cleaned = self.extract_json(&json_response);

        let entities: ExtractedEntities = serde_json::from_str(&cleaned)?;

        if !self.validate_entities(&entities) {
            warn!("Pass {} produced invalid entities, retrying...", pass_num);
            anyhow::bail!("Invalid entity structure");
        }

        Ok(entities)
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

    fn validate_entities(&self, entities: &ExtractedEntities) -> bool {
        for port in &entities.ports {
            if port.port == 0 {
                return false;
            }
            if port.protocol.is_empty() {
                return false;
            }
        }

        for vuln in &entities.vulnerabilities {
            if vuln.name.is_empty() || vuln.severity.is_empty() {
                return false;
            }
        }

        true
    }

    fn merge_with_union(&self, passes: &[ExtractedEntities]) -> ExtractedEntities {
        let mut merged = ExtractedEntities::default();

        for entities in passes {
            for ip in &entities.ips {
                if !merged.ips.contains(ip) {
                    merged.ips.push(ip.clone());
                }
            }

            for domain in &entities.domains {
                if !merged.domains.contains(domain) {
                    merged.domains.push(domain.clone());
                }
            }

            for url in &entities.urls {
                if !merged.urls.contains(url) {
                    merged.urls.push(url.clone());
                }
            }

            for port in &entities.ports {
                let existing = merged
                    .ports
                    .iter_mut()
                    .find(|p| p.port == port.port && p.protocol == port.protocol);

                match existing {
                    Some(existing_port) => {
                        // Merge additional information if this pass has more detail
                        if existing_port.service.is_none() && port.service.is_some() {
                            existing_port.service = port.service.clone();
                        }
                        if existing_port.version.is_none() && port.version.is_some() {
                            existing_port.version = port.version.clone();
                        }
                    }
                    None => {
                        merged.ports.push(port.clone());
                    }
                }
            }

            for vuln in &entities.vulnerabilities {
                let existing = merged
                    .vulnerabilities
                    .iter_mut()
                    .find(|v| v.name == vuln.name);

                match existing {
                    Some(existing_vuln) => {
                        // Prefer more severe rating if different
                        if existing_vuln.severity.to_lowercase() == "low"
                            && vuln.severity.to_lowercase() != "low"
                        {
                            existing_vuln.severity = vuln.severity.clone();
                        }
                        // Merge description if current is empty or shorter
                        if existing_vuln.description.len() < vuln.description.len() {
                            existing_vuln.description = vuln.description.clone();
                        }
                    }
                    None => {
                        merged.vulnerabilities.push(vuln.clone());
                    }
                }
            }

            for finding in &entities.findings {
                if !merged.findings.contains(finding) {
                    merged.findings.push(finding.clone());
                }
            }
        }

        merged.ips.sort();
        merged.domains.sort();
        merged.urls.sort();
        merged.findings.sort();

        merged
    }

    fn calculate_consistency(&self, passes: &[ExtractedEntities]) -> f64 {
        if passes.len() <= 1 {
            return 1.0;
        }

        let mut consistency_scores = Vec::new();

        for i in 0..passes.len() {
            for j in (i + 1)..passes.len() {
                let score = self.compare_entities(&passes[i], &passes[j]);
                consistency_scores.push(score);
            }
        }

        if consistency_scores.is_empty() {
            return 1.0;
        }

        consistency_scores.iter().sum::<f64>() / consistency_scores.len() as f64
    }

    fn compare_entities(&self, a: &ExtractedEntities, b: &ExtractedEntities) -> f64 {
        let mut total_score = 0.0;
        let mut categories = 0;

        let ip_score = self.jaccard_similarity(&a.ips, &b.ips);
        total_score += ip_score;
        categories += 1;

        let domain_score = self.jaccard_similarity(&a.domains, &b.domains);
        total_score += domain_score;
        categories += 1;

        let url_score = self.jaccard_similarity(&a.urls, &b.urls);
        total_score += url_score;
        categories += 1;

        let port_score = self.port_similarity(&a.ports, &b.ports);
        total_score += port_score;
        categories += 1;

        let vuln_score = self.vulnerability_similarity(&a.vulnerabilities, &b.vulnerabilities);
        total_score += vuln_score;
        categories += 1;

        let finding_score = self.jaccard_similarity(&a.findings, &b.findings);
        total_score += finding_score;
        categories += 1;

        if categories == 0 {
            return 1.0;
        }

        total_score / categories as f64
    }

    fn jaccard_similarity<T: Eq + std::hash::Hash + Clone>(&self, a: &[T], b: &[T]) -> f64 {
        if a.is_empty() && b.is_empty() {
            return 1.0;
        }

        let set_a: std::collections::HashSet<_> = a.iter().collect();
        let set_b: std::collections::HashSet<_> = b.iter().collect();

        let intersection = set_a.intersection(&set_b).count();
        let union = set_a.union(&set_b).count();

        if union == 0 {
            return 1.0;
        }

        intersection as f64 / union as f64
    }

    fn port_similarity(
        &self,
        a: &[super::extractor::PortInfo],
        b: &[super::extractor::PortInfo],
    ) -> f64 {
        if a.is_empty() && b.is_empty() {
            return 1.0;
        }

        let ports_a: Vec<_> = a.iter().map(|p| (p.port, &p.protocol)).collect();
        let ports_b: Vec<_> = b.iter().map(|p| (p.port, &p.protocol)).collect();

        let set_a: std::collections::HashSet<_> = ports_a.iter().collect();
        let set_b: std::collections::HashSet<_> = ports_b.iter().collect();

        let intersection = set_a.intersection(&set_b).count();
        let union = set_a.union(&set_b).count();

        if union == 0 {
            return 1.0;
        }

        intersection as f64 / union as f64
    }

    fn vulnerability_similarity(
        &self,
        a: &[super::extractor::Vulnerability],
        b: &[super::extractor::Vulnerability],
    ) -> f64 {
        if a.is_empty() && b.is_empty() {
            return 1.0;
        }

        let names_a: Vec<_> = a.iter().map(|v| &v.name).collect();
        let names_b: Vec<_> = b.iter().map(|v| &v.name).collect();

        let set_a: std::collections::HashSet<_> = names_a.iter().collect();
        let set_b: std::collections::HashSet<_> = names_b.iter().collect();

        let intersection = set_a.intersection(&set_b).count();
        let union = set_a.union(&set_b).count();

        if union == 0 {
            return 1.0;
        }

        intersection as f64 / union as f64
    }

    fn generate_warnings(&self, consistency: f64, passes: &[ExtractedEntities]) -> Vec<String> {
        let mut warnings = Vec::new();

        if consistency < 0.5 {
            warnings.push(format!(
                "Low consistency score ({:.2}): Results vary significantly between parsing passes",
                consistency
            ));
        } else if consistency < 0.8 {
            warnings.push(format!(
                "Medium consistency score ({:.2}): Some variation detected in results",
                consistency
            ));
        }

        if passes.len() < self.num_passes {
            warnings.push(format!(
                "Only {}/{} parsing passes succeeded",
                passes.len(),
                self.num_passes
            ));
        }

        let vuln_counts: Vec<_> = passes.iter().map(|p| p.vulnerabilities.len()).collect();
        if !vuln_counts.is_empty() {
            let max_vulns = *vuln_counts.iter().max().unwrap();
            let min_vulns = *vuln_counts.iter().min().unwrap();
            if max_vulns > min_vulns {
                warnings.push(format!(
                    "Vulnerability count varied between passes (min: {}, max: {})",
                    min_vulns, max_vulns
                ));
            }
        }

        warnings
    }
}

impl Default for ConsistencyChecker {
    fn default() -> Self {
        Self::new(3, false)
    }
}
