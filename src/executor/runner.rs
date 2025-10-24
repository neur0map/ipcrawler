use super::queue::{Task, TaskId, TaskStatus};
use crate::system::{get_command_path, ScriptSecurity};
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Instant;
use tokio::process::Command;
use tokio::sync::{mpsc, Mutex, Semaphore};
use tokio::time::timeout;

#[derive(Clone)]
pub struct TaskResult {
    #[allow(dead_code)]
    pub task_id: TaskId,
    pub tool_name: String,
    pub target: String,
    pub port: Option<u16>,
    pub actual_command: String,
    pub status: TaskStatus,
    pub stdout: String,
    pub stderr: String,
}

pub type ExecutionState = Arc<Mutex<HashMap<TaskId, TaskStatus>>>;
pub type UpdateSender = mpsc::UnboundedSender<TaskUpdate>;
#[allow(dead_code)]
pub type UpdateReceiver = mpsc::UnboundedReceiver<TaskUpdate>;

#[derive(Debug, Clone)]
pub enum TaskUpdate {
    Started {
        task_id: TaskId,
        tool_name: String,
        target: String,
        port: Option<u16>,
    },
    Completed {
        task_id: TaskId,
        #[allow(dead_code)]
        result: String,
        stdout: String,
        stderr: String,
    },
    Failed {
        task_id: TaskId,
        error: String,
        stdout: String,
        stderr: String,
    },
    Progress {
        queued: usize,
        running: usize,
        completed: usize,
    },
}

pub struct TaskRunner {
    max_concurrent: usize,
    state: ExecutionState,
}

impl TaskRunner {
    pub fn new(max_concurrent: usize) -> Self {
        Self {
            max_concurrent,
            state: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub async fn run_tasks(&self, tasks: Vec<Task>, update_tx: UpdateSender) -> Vec<TaskResult> {
        let semaphore = Arc::new(Semaphore::new(self.max_concurrent));
        let mut handles = Vec::new();
        let results = Arc::new(Mutex::new(Vec::new()));

        let total_tasks = tasks.len();

        // Send initial progress update so TUI shows correct total count from the start
        let _ = update_tx.send(TaskUpdate::Progress {
            queued: total_tasks,
            running: 0,
            completed: 0,
        });

        for task in tasks {
            let sem_clone = Arc::clone(&semaphore);
            let state_clone = Arc::clone(&self.state);
            let results_clone = Arc::clone(&results);
            let update_tx_clone = update_tx.clone();

            let handle = tokio::spawn(async move {
                let _permit = sem_clone.acquire().await.unwrap();

                let result = Self::execute_task(task, state_clone, update_tx_clone).await;

                results_clone.lock().await.push(result);
            });

            handles.push(handle);
        }

        for handle in handles {
            let _ = handle.await;

            let state = self.state.lock().await;
            let running = state.values().filter(|s| s.is_running()).count();
            let completed = state.values().filter(|s| s.is_done()).count();
            let queued = total_tasks - running - completed;

            drop(state);

            let _ = update_tx.send(TaskUpdate::Progress {
                queued,
                running,
                completed,
            });
        }

        let final_results = results.lock().await;
        final_results.clone()
    }

    /// Checks if command references a shell script and validates/prepares it
    fn prepare_script_if_needed(command: &str) -> anyhow::Result<Option<PathBuf>> {
        let parts: Vec<&str> = command.split_whitespace().collect();
        if parts.is_empty() {
            return Ok(None);
        }

        let first_arg = parts[0];

        // Check if it's a .sh file
        if first_arg.ends_with(".sh") {
            let script_path = if first_arg.starts_with('/') || first_arg.starts_with("./") {
                // Absolute or relative path
                PathBuf::from(first_arg)
            } else {
                // Just filename, look in tools/scripts/
                PathBuf::from("tools/scripts").join(first_arg)
            };

            if !script_path.exists() {
                anyhow::bail!("Script not found: {}", script_path.display());
            }

            // Validate script security (minimal output)
            match ScriptSecurity::validate_script(&script_path) {
                Ok(validation) => {
                    let summary = validation.summary();

                    // Only block truly dangerous scripts
                    if !validation.is_safe {
                        validation.print_report();
                        anyhow::bail!("Script blocked: {}", script_path.display());
                    }

                    // Log validation result for debugging (OK, Warning, or BLOCKED)
                    if summary != "OK" {
                        eprintln!("Script validation: {} - {}", script_path.display(), summary);
                    }
                }
                Err(e) => {
                    anyhow::bail!("Script validation error: {}", e);
                }
            }

            // Make script executable automatically
            let _ = ScriptSecurity::make_executable(&script_path);

            Ok(Some(script_path))
        } else {
            Ok(None)
        }
    }

    async fn execute_task(
        task: Task,
        state: ExecutionState,
        update_tx: UpdateSender,
    ) -> TaskResult {
        let started_at = Instant::now();

        {
            let mut state = state.lock().await;
            state.insert(task.id.clone(), TaskStatus::Running { started_at });
        }

        let _ = update_tx.send(TaskUpdate::Started {
            task_id: task.id.clone(),
            tool_name: task.tool_name.clone(),
            target: task.target.clone(),
            port: task.port,
        });

        // Check and prepare script if needed
        let (actual_command, program, args) = match Self::prepare_script_if_needed(&task.command) {
            Ok(Some(script_path)) => {
                // Script validated and made executable, use script path
                let script_path_str = script_path.to_string_lossy().to_string();
                let parts: Vec<&str> = task.command.split_whitespace().collect();
                let script_args = if parts.len() > 1 { &parts[1..] } else { &[] };
                let actual_cmd = format!("{} {}", script_path_str, script_args.join(" "));
                (actual_cmd, script_path_str, script_args.to_vec())
            }
            Ok(None) => {
                // Not a script, proceed normally
                let parts: Vec<&str> = task.command.split_whitespace().collect();
                if parts.is_empty() {
                    let error = "Empty command".to_string();
                    let _ = update_tx.send(TaskUpdate::Failed {
                        task_id: task.id.clone(),
                        error: error.clone(),
                        stdout: String::new(),
                        stderr: error.clone(),
                    });

                    let failed_status = TaskStatus::Failed {
                        error: error.clone(),
                    };
                    state
                        .lock()
                        .await
                        .insert(task.id.clone(), failed_status.clone());

                    return TaskResult {
                        task_id: task.id,
                        tool_name: task.tool_name,
                        target: task.target,
                        port: task.port,
                        actual_command: task.command,
                        status: failed_status,
                        stdout: String::new(),
                        stderr: error,
                    };
                }

                // Get the full path to the binary, especially important when running as root
                let binary = parts[0];
                let program = get_command_path(binary).unwrap_or_else(|| binary.to_string());

                (task.command.clone(), program, parts[1..].to_vec())
            }
            Err(e) => {
                let error = format!("Script validation failed: {}", e);
                let _ = update_tx.send(TaskUpdate::Failed {
                    task_id: task.id.clone(),
                    error: error.clone(),
                    stdout: String::new(),
                    stderr: error.clone(),
                });

                let failed_status = TaskStatus::Failed {
                    error: error.clone(),
                };
                state
                    .lock()
                    .await
                    .insert(task.id.clone(), failed_status.clone());

                return TaskResult {
                    task_id: task.id,
                    tool_name: task.tool_name,
                    target: task.target,
                    port: task.port,
                    actual_command: task.command,
                    status: failed_status,
                    stdout: String::new(),
                    stderr: error,
                };
            }
        };

        let command_result = timeout(
            task.timeout,
            Command::new(program)
                .args(args)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output(),
        )
        .await;

        let (status, stdout, stderr) = match command_result {
            Ok(Ok(output)) => {
                let duration = started_at.elapsed();
                let exit_code = output.status.code().unwrap_or(-1);

                let stdout_str = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr_str = String::from_utf8_lossy(&output.stderr).to_string();

                let status = TaskStatus::Completed {
                    duration,
                    exit_code,
                };

                let _ = update_tx.send(TaskUpdate::Completed {
                    task_id: task.id.clone(),
                    result: format!("Exit code: {}", exit_code),
                    stdout: stdout_str.clone(),
                    stderr: stderr_str.clone(),
                });

                (status, stdout_str, stderr_str)
            }
            Ok(Err(e)) => {
                let error = format!("Failed to execute: {}", e);
                let _ = update_tx.send(TaskUpdate::Failed {
                    task_id: task.id.clone(),
                    error: error.clone(),
                    stdout: String::new(),
                    stderr: error.clone(),
                });

                (
                    TaskStatus::Failed {
                        error: error.clone(),
                    },
                    String::new(),
                    error,
                )
            }
            Err(_) => {
                let error = format!("Timed out after {:?}", task.timeout);
                let _ = update_tx.send(TaskUpdate::Failed {
                    task_id: task.id.clone(),
                    error: error.clone(),
                    stdout: String::new(),
                    stderr: error.clone(),
                });

                (TaskStatus::TimedOut, String::new(), error)
            }
        };

        state.lock().await.insert(task.id.clone(), status.clone());

        TaskResult {
            task_id: task.id,
            tool_name: task.tool_name,
            target: task.target,
            port: task.port,
            actual_command,
            status,
            stdout,
            stderr,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use std::time::Duration;

    #[tokio::test]
    async fn test_simple_task_execution() {
        let runner = TaskRunner::new(2);
        let (tx, _rx) = mpsc::unbounded_channel();

        let task = Task {
            id: TaskId::new("echo", "test", None),
            tool_name: "echo".to_string(),
            target: "test".to_string(),
            port: None,
            output_file: PathBuf::from("/tmp/test.json"),
            command: "echo hello".to_string(),
            timeout: Duration::from_secs(5),
        };

        let results = runner.run_tasks(vec![task], tx).await;

        assert_eq!(results.len(), 1);
        assert!(matches!(results[0].status, TaskStatus::Completed { .. }));
    }
}
