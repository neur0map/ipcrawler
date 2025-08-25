use super::command::{execute, CommandResult};
use anyhow::Result;
use std::path::Path;

#[allow(dead_code)]
pub async fn run_nmap(target: &str, output_file: &Path, cwd: &Path) -> Result<CommandResult> {
    let args = vec![
        "-sS", // SYN scan
        "-sV", // Version detection
        "-T4", // Timing template
        "-oX", // XML output
        output_file.to_str().unwrap(),
        target,
    ];

    execute("nmap", &args, cwd, Some(300000)).await // 5 minute timeout
}

#[allow(dead_code)]
pub async fn run_curl(url: &str, output_file: Option<&Path>, cwd: &Path) -> Result<CommandResult> {
    let mut args = vec![
        "-s", // Silent
        "-L", // Follow redirects
        "-m", "10", // Max time 10 seconds
        "-I", // Headers only
        url,
    ];

    if let Some(out) = output_file {
        args.extend(&["-o", out.to_str().unwrap()]);
    }

    execute("curl", &args, cwd, Some(15000)).await // 15 second timeout
}
