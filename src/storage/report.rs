use crate::parser::ExtractedEntities;
use crate::templates::executor::ExecutionResult;
use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::Path;
use tokio::fs;
use tracing::info;

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanReport {
    pub target: String,
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub duration: u64,
    pub tools_executed: Vec<ToolExecution>,
    pub entities: ExtractedEntities,
    pub summary: ScanSummary,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolExecution {
    pub name: String,
    pub success: bool,
    pub duration_secs: f64,
    pub output_file: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanSummary {
    pub total_tools: usize,
    pub successful_tools: usize,
    pub failed_tools: usize,
    pub total_ips: usize,
    pub total_domains: usize,
    pub total_urls: usize,
    pub total_ports: usize,
    pub total_vulnerabilities: usize,
}

pub struct ReportManager;

impl ReportManager {
    pub async fn save_entities(entities: &ExtractedEntities, path: &Path) -> Result<()> {
        let json =
            serde_json::to_string_pretty(entities).context("Failed to serialize entities")?;

        fs::write(path, json)
            .await
            .context("Failed to write entities file")?;

        info!("Saved extracted entities to: {}", path.display());
        Ok(())
    }

    pub async fn save_report(report: &ScanReport, path: &Path) -> Result<()> {
        let json = serde_json::to_string_pretty(report).context("Failed to serialize report")?;

        fs::write(path, json)
            .await
            .context("Failed to write report file")?;

        info!("Saved scan report to: {}", path.display());
        Ok(())
    }

    pub fn build_report(
        target: String,
        start_time: DateTime<Utc>,
        results: Vec<ExecutionResult>,
        entities: ExtractedEntities,
    ) -> ScanReport {
        let end_time = Utc::now();
        let duration = (end_time - start_time).num_seconds() as u64;

        let tools_executed: Vec<ToolExecution> = results
            .iter()
            .map(|r| ToolExecution {
                name: r.template_name.clone(),
                success: r.success,
                duration_secs: r.duration.as_secs_f64(),
                output_file: r.output_file.clone(),
            })
            .collect();

        let successful_tools = tools_executed.iter().filter(|t| t.success).count();
        let failed_tools = tools_executed.len() - successful_tools;

        let summary = ScanSummary {
            total_tools: tools_executed.len(),
            successful_tools,
            failed_tools,
            total_ips: entities.ips.len(),
            total_domains: entities.domains.len(),
            total_urls: entities.urls.len(),
            total_ports: entities.ports.len(),
            total_vulnerabilities: entities.vulnerabilities.len(),
        };

        ScanReport {
            target,
            start_time,
            end_time,
            duration,
            tools_executed,
            entities,
            summary,
        }
    }
}
