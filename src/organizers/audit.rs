use crate::config::GlobalConfig;
use crate::core::models::RunDirs;
use anyhow::{bail, Result};
use std::fs;

#[allow(dead_code)]
const MIN_FREE_SPACE_MB: u64 = 100;

#[allow(dead_code)]
pub fn preflight_checks(dirs: &RunDirs) -> Result<()> {
    preflight_checks_with_config(dirs, None)
}

pub fn preflight_checks_with_config(dirs: &RunDirs, config: Option<&GlobalConfig>) -> Result<()> {
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
        if let Err(e) = check_ulimit_with_config(config) {
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
fn check_ulimit_with_config(config: Option<&GlobalConfig>) -> Result<()> {
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

    // Calculate actual requirement based on configuration
    let required_fds = if let Some(config) = config {
        // Base requirement: 100 for basic operations
        // Add requirement for concurrent scans
        let base_fds = 100;
        let scan_fds = config.concurrency.max_total_scans * 2; // 2 FDs per concurrent operation
        base_fds + scan_fds
    } else {
        // Conservative default when no config available
        512
    };

    if rlim.rlim_cur < required_fds as u64 {
        // Provide helpful error message with actual requirement and how to fix
        bail!(
            "File descriptor limit too low: {} (minimum: {})\n\
            Quick fix: Run 'ulimit -n {}' before scanning\n\
            For permanent fix, add 'ulimit -n {}' to your shell profile",
            rlim.rlim_cur,
            required_fds,
            required_fds * 2,
            required_fds * 2
        );
    }

    Ok(())
}
