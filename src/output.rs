use anyhow::{Context, Result};
use std::fs;
use std::path::Path;
use tokio::fs as tokio_fs;

#[derive(Clone)]
pub struct OutputManager {
    output_dir: String,
    raw_dir: String,
    reports_dir: String,
}

impl OutputManager {
    pub fn new(output_dir: &str) -> Result<Self> {
        let raw_dir = Path::new(output_dir).join("raw").to_string_lossy().to_string();
        let reports_dir = Path::new(output_dir).join("reports").to_string_lossy().to_string();
        
        // Create directories if they don't exist
        fs::create_dir_all(&raw_dir)
            .with_context(|| format!("Failed to create raw output directory: {}", raw_dir))?;
        fs::create_dir_all(&reports_dir)
            .with_context(|| format!("Failed to create reports directory: {}", reports_dir))?;
        
        Ok(OutputManager {
            output_dir: output_dir.to_string(),
            raw_dir,
            reports_dir,
        })
    }
    
    pub async fn save_raw_output(&self, filename: &str, content: &str) -> Result<()> {
        let filepath = self.get_raw_output_path(filename);
        tokio_fs::write(&filepath, content).await
            .with_context(|| format!("Failed to write raw output to: {}", filepath))?;
        Ok(())
    }
    
    pub async fn save_report(&self, filename: &str, content: &str) -> Result<()> {
        let filepath = self.get_report_path(filename);
        tokio_fs::write(&filepath, content).await
            .with_context(|| format!("Failed to write report to: {}", filepath))?;
        Ok(())
    }
    
    pub fn get_raw_output_path(&self, filename: &str) -> String {
        Path::new(&self.raw_dir).join(filename).to_string_lossy().to_string()
    }
    
    pub fn get_report_path(&self, filename: &str) -> String {
        Path::new(&self.reports_dir).join(filename).to_string_lossy().to_string()
    }
    
    pub fn get_output_dir(&self) -> &str {
        &self.output_dir
    }
}
