use crate::core::models::RunDirs;
use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};

pub fn prepare_run_dirs(run_id: &str) -> Result<RunDirs> {
    let base = PathBuf::from("artifacts");
    let root = base.join("runs").join(run_id);

    let dirs = RunDirs {
        root: root.clone(),
        scans: root.join("scans"),
        loot: root.join("loot"),
        report: root.join("report"),
        logs: base.join("logs"),
    };

    // Create all directories
    for dir in &[
        &dirs.root,
        &dirs.scans,
        &dirs.loot,
        &dirs.report,
        &dirs.logs,
    ] {
        fs::create_dir_all(dir)
            .with_context(|| format!("Failed to create directory: {:?}", dir))?;
    }

    // Verify writability
    verify_writable(&dirs.logs)?;

    // fsync directories on Unix for durability
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        for dir in &[&dirs.root, &dirs.scans, &dirs.loot, &dirs.report] {
            let _ = fs::OpenOptions::new()
                .read(true)
                .custom_flags(libc::O_DIRECTORY)
                .open(dir)?
                .sync_all();
        }
    }

    Ok(dirs)
}

fn verify_writable(path: &Path) -> Result<()> {
    let test_file = path.join(".write_test");
    fs::write(&test_file, b"test")
        .with_context(|| format!("Directory not writable: {:?}", path))?;
    fs::remove_file(&test_file)
        .with_context(|| format!("Failed to remove test file: {:?}", test_file))?;
    Ok(())
}
