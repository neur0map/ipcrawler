use anyhow::{Result, bail};
use crate::core::models::RunDirs;
use std::fs;

const MIN_FREE_SPACE_MB: u64 = 100;

pub fn preflight_checks(dirs: &RunDirs) -> Result<()> {
    let mut errors = Vec::new();
    
    // Check free space
    if let Err(e) = check_free_space(&dirs.root) {
        errors.push(format!("Disk space: {}", e));
    }
    
    // Verify write permissions
    for (name, path) in &[
        ("root", &dirs.root),
        ("scans", &dirs.scans),
        ("loot", &dirs.loot),
        ("report", &dirs.report),
        ("logs", &dirs.logs),
    ] {
        if let Err(e) = verify_writable(path) {
            errors.push(format!("{}: {}", name, e));
        }
    }
    
    // Check file descriptor limits on Unix
    #[cfg(unix)]
    {
        if let Err(e) = check_ulimit() {
            errors.push(format!("File descriptors: {}", e));
        }
    }
    
    if !errors.is_empty() {
        bail!("Preflight checks failed:\n{}", errors.join("\n"));
    }
    
    Ok(())
}

fn check_free_space(path: &std::path::Path) -> Result<()> {
    // Simple check - just ensure directory exists
    // Full implementation would use platform-specific APIs
    if !path.exists() {
        bail!("Path does not exist: {:?}", path);
    }
    Ok(())
}

fn verify_writable(path: &std::path::Path) -> Result<()> {
    let test_file = path.join(".audit_test");
    fs::write(&test_file, b"test")?;
    fs::remove_file(&test_file)?;
    Ok(())
}

#[cfg(unix)]
fn check_ulimit() -> Result<()> {
    use libc::{getrlimit, rlimit, RLIMIT_NOFILE};
    
    let mut rlim = rlimit {
        rlim_cur: 0,
        rlim_max: 0,
    };
    
    unsafe {
        if getrlimit(RLIMIT_NOFILE, &mut rlim) != 0 {
            bail!("Failed to get file descriptor limit");
        }
    }
    
    if rlim.rlim_cur < 1024 {
        bail!("File descriptor limit too low: {} (minimum: 1024)", rlim.rlim_cur);
    }
    
    Ok(())
}