use anyhow::{Result, bail};
use std::fs;
use crate::core::models::RunDirs;

pub fn validate_reports(dirs: &RunDirs) -> Result<()> {
    let required_files = vec![
        dirs.report.join("summary.txt"),
        dirs.report.join("summary.md"),
        dirs.report.join("summary.json"),
    ];
    
    for file in required_files {
        if !file.exists() {
            bail!("Required report file missing: {:?}", file);
        }
        
        let metadata = fs::metadata(&file)?;
        if metadata.len() == 0 {
            bail!("Report file is empty: {:?}", file);
        }
    }
    
    tracing::info!("All reports validated successfully");
    Ok(())
}
