use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use tokio::fs;
use tracing::info;

pub struct OutputManager {
    base_dir: PathBuf,
}

impl OutputManager {
    pub fn new(base_dir: PathBuf) -> Self {
        Self { base_dir }
    }

    pub async fn initialize(&self) -> Result<()> {
        fs::create_dir_all(&self.base_dir)
            .await
            .context("Failed to create base output directory")?;

        let raw_dir = self.base_dir.join("raw");
        fs::create_dir_all(&raw_dir)
            .await
            .context("Failed to create raw output directory")?;

        info!("Initialized output directory: {}", self.base_dir.display());
        Ok(())
    }

    /// Get the base output directory path
    #[allow(dead_code)]
    pub fn get_base_dir(&self) -> &Path {
        &self.base_dir
    }

    pub fn get_raw_dir(&self) -> PathBuf {
        self.base_dir.join("raw")
    }

    pub fn get_entities_file(&self) -> PathBuf {
        self.base_dir.join("entities.json")
    }

    pub fn get_report_file(&self) -> PathBuf {
        self.base_dir.join("report.json")
    }

    pub fn get_html_report_file(&self) -> PathBuf {
        self.base_dir.join("report.html")
    }

    pub fn get_markdown_report_file(&self) -> PathBuf {
        self.base_dir.join("report.md")
    }
}
