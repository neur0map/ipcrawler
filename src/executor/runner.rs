use super::queue::{Task, TaskId, TaskStatus};
use crate::system::ScriptSecurity;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Instant;
use tokio::process::Command;
use tokio::sync::{mpsc, Mutex, Semaphore};
use tokio::time::timeout;

#[derive(Clone)]
#[allow(dead_code)]
pub struct TaskResult {
    pub task_id: TaskId,
    pub tool_name: String,
    pub target: String,
    pub port: Option<u16>,
    pub status: TaskStatus,
    pub stdout: String,
    pub stderr: String,
}

pub type ExecutionState = Arc<Mutex<HashMap<TaskId, TaskStatus>>>;
pub type UpdateSender = mpsc::UnboundedSender<TaskUpdate>;
#[allow(dead_code)]
pub type UpdateReceiver = mpsc::UnboundedReceiver<TaskUpdate>;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub enum TaskUpdate {
    Started {
        task_id: TaskId,
        tool_name: String,
        target: String,
        port: Option<u16>,
    },
    Completed {
        task_id: TaskId,
        result: String,
    },
    Failed {
        task_id: TaskId,
        error: String,
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

            // Validate script security
            match ScriptSecurity::validate_script(&script_path) {
                Ok(validation) => {
                    validation.print_report();

                    if !validation.is_safe {
                        anyhow::bail!(
                            "Script failed security validation: {}. Contains dangerous commands.",
                            script_path.display()
                        );
                    }

                    if !validation.suspicious_patterns.is_empty() {
                        eprintln!(
                            "WARNING: Script {} contains suspicious patterns. Proceeding with caution...",
                            script_path.display()
                        );
                    }
                }
                Err(e) => {
                    anyhow::bail!("Failed to validate script: {}", e);
                }
            }

            // Make script executable automatically
            if let Err(e) = ScriptSecurity::make_executable(&script_path) {
                eprintln!("Warning: Failed to make script executable: {}", e);
            }

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
        match Self::prepare_script_if_needed(&task.command) {
            Ok(Some(_script_path)) => {
                // Script validated and made executable
                println!("Script validated and prepared for execution");
            }
            Ok(None) => {
                // Not a script, proceed normally
            }
            Err(e) => {
                let error = format!("Script validation failed: {}", e);
                let _ = update_tx.send(TaskUpdate::Failed {
                    task_id: task.id.clone(),
                    error: error.clone(),
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
                    status: failed_status,
                    stdout: String::new(),
                    stderr: error,
                };
            }
        }

        let parts: Vec<&str> = task.command.split_whitespace().collect();
        if parts.is_empty() {
            let error = "Empty command".to_string();
            let _ = update_tx.send(TaskUpdate::Failed {
                task_id: task.id.clone(),
                error: error.clone(),
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
                status: failed_status,
                stdout: String::new(),
                stderr: error,
            };
        }

        let program = parts[0];
        let args = &parts[1..];

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
                });

                (status, stdout_str, stderr_str)
            }
            Ok(Err(e)) => {
                let error = format!("Failed to execute: {}", e);
                let _ = update_tx.send(TaskUpdate::Failed {
                    task_id: task.id.clone(),
                    error: error.clone(),
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
            status,
            stdout,
            stderr,
        }
    }

    #[allow(dead_code)]
    pub async fn get_status(&self, task_id: &TaskId) -> Option<TaskStatus> {
        let state = self.state.lock().await;
        state.get(task_id).cloned()
    }

    #[allow(dead_code)]
    pub async fn get_all_statuses(&self) -> HashMap<TaskId, TaskStatus> {
        let state = self.state.lock().await;
        state.clone()
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
