use crate::core::errors::{ExecError, IpcrawlerError};
use anyhow::{Context, Result};
use std::path::Path;
use std::process::Stdio;
use std::time::{Duration, Instant};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::time::timeout;

#[allow(dead_code)]
pub struct CommandResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
    pub duration_ms: u128,
    pub pid: Option<u32>,
}

pub async fn execute(
    tool: &str,
    args: &[&str],
    cwd: &Path,
    timeout_ms: Option<u64>,
) -> Result<CommandResult> {
    let start = Instant::now();
    let timeout_duration = timeout_ms.map(Duration::from_millis);

    tracing::debug!("Executing: {} {:?} in {:?}", tool, args, cwd);

    let mut cmd = Command::new(tool);
    cmd.args(args)
        .current_dir(cwd)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);

    let mut child = cmd
        .spawn()
        .with_context(|| format!("Failed to spawn {}", tool))?;

    let pid = child.id();

    let stdout_handle = child.stdout.take().expect("stdout");
    let stderr_handle = child.stderr.take().expect("stderr");

    // Read outputs incrementally to avoid buffer stalls
    let stdout_reader = BufReader::new(stdout_handle);
    let stderr_reader = BufReader::new(stderr_handle);

    let (stdout_result, stderr_result, wait_result) = tokio::join!(
        read_lines(stdout_reader),
        read_lines(stderr_reader),
        async {
            if let Some(duration) = timeout_duration {
                timeout(duration, child.wait()).await
            } else {
                Ok(child.wait().await)
            }
        }
    );

    let duration_ms = start.elapsed().as_millis();

    let status = match wait_result {
        Ok(Ok(status)) => status,
        Ok(Err(e)) => {
            return Err(IpcrawlerError::Exec(ExecError {
                tool: tool.to_string(),
                args: args.iter().map(|s| s.to_string()).collect(),
                cwd: cwd.display().to_string(),
                exit_code: None,
                stderr_tail: format!("Process error: {}", e),
                duration_ms,
            })
            .into());
        }
        Err(_) => {
            // Timeout occurred
            let _ = child.kill().await;
            return Err(IpcrawlerError::Exec(ExecError {
                tool: tool.to_string(),
                args: args.iter().map(|s| s.to_string()).collect(),
                cwd: cwd.display().to_string(),
                exit_code: None,
                stderr_tail: format!("Command timed out after {}ms", timeout_ms.unwrap()),
                duration_ms,
            })
            .into());
        }
    };

    let exit_code = status.code().unwrap_or(-1);
    let stdout = stdout_result?;
    let stderr = stderr_result?;

    if !status.success() {
        let stderr_lines: Vec<_> = stderr.lines().collect();
        let stderr_tail = stderr_lines
            .iter()
            .rev()
            .take(10)
            .rev()
            .cloned()
            .collect::<Vec<_>>()
            .join("\n");

        return Err(IpcrawlerError::Exec(ExecError {
            tool: tool.to_string(),
            args: args.iter().map(|s| s.to_string()).collect(),
            cwd: cwd.display().to_string(),
            exit_code: Some(exit_code),
            stderr_tail,
            duration_ms,
        })
        .into());
    }

    Ok(CommandResult {
        stdout,
        stderr,
        exit_code,
        duration_ms,
        pid,
    })
}

async fn read_lines<R>(reader: BufReader<R>) -> Result<String>
where
    R: tokio::io::AsyncRead + Unpin,
{
    let mut lines = Vec::new();
    let mut reader = reader.lines();

    while let Some(line) = reader.next_line().await? {
        lines.push(line);
    }

    Ok(lines.join("\n"))
}

// Synchronous wrapper for non-async contexts
#[allow(dead_code)]
pub fn execute_sync(
    tool: &str,
    args: &[&str],
    cwd: &Path,
    timeout_ms: Option<u64>,
) -> Result<CommandResult> {
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(execute(tool, args, cwd, timeout_ms))
}
