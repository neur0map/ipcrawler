use std::fs;
use std::io::Write;
use std::path::Path;
use anyhow::{Result, Context};

pub fn atomic_write<P: AsRef<Path>>(path: P, content: &[u8]) -> Result<()> {
    let path = path.as_ref();
    let parent = path.parent()
        .ok_or_else(|| anyhow::anyhow!("Invalid path: no parent directory"))?;
    
    if !parent.exists() {
        fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create parent directory: {:?}", parent))?;
    }
    
    let tmp_path = path.with_extension("tmp");
    
    let mut file = fs::File::create(&tmp_path)
        .with_context(|| format!("Failed to create temp file: {:?}", tmp_path))?;
    
    file.write_all(content)
        .with_context(|| format!("Failed to write to temp file: {:?}", tmp_path))?;
    
    file.sync_all()
        .with_context(|| format!("Failed to sync temp file: {:?}", tmp_path))?;
    
    fs::rename(&tmp_path, path)
        .with_context(|| format!("Failed to rename {:?} to {:?}", tmp_path, path))?;
    
    Ok(())
}