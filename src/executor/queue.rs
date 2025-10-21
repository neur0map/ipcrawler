use crate::config::Tool;
use std::collections::VecDeque;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct TaskId(pub String);

impl TaskId {
    pub fn new(tool_name: &str, target: &str, port: Option<u16>) -> Self {
        let id = match port {
            Some(p) => format!("{}_{}_{}",tool_name, target.replace(['.', ':'], "_"), p),
            None => format!("{}_{}", tool_name, target.replace(['.', ':'], "_")),
        };
        TaskId(id)
    }
}

#[derive(Debug, Clone)]
pub struct Task {
    pub id: TaskId,
    pub tool_name: String,
    pub target: String,
    pub port: Option<u16>,
    #[allow(dead_code)]
    pub output_file: PathBuf,
    pub command: String,
    pub timeout: Duration,
}

impl Task {
    pub fn new(
        tool: &Tool,
        target: String,
        port: Option<u16>,
        output_dir: &Path,
    ) -> anyhow::Result<Self> {
        let id = TaskId::new(&tool.name, &target, port);

        let output_file = output_dir.join(format!("{}.json", id.0));

        let command = tool.render_command(
            &target,
            port,
            output_file.to_str().unwrap_or("output.json"),
        )?;

        Ok(Task {
            id,
            tool_name: tool.name.clone(),
            target,
            port,
            output_file,
            command,
            timeout: Duration::from_secs(tool.timeout),
        })
    }
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub enum TaskStatus {
    Queued,
    Running { started_at: Instant },
    Completed { duration: Duration, exit_code: i32 },
    Failed { error: String },
    TimedOut,
}

impl TaskStatus {
    pub fn is_done(&self) -> bool {
        matches!(
            self,
            TaskStatus::Completed { .. } | TaskStatus::Failed { .. } | TaskStatus::TimedOut
        )
    }

    pub fn is_running(&self) -> bool {
        matches!(self, TaskStatus::Running { .. })
    }
}

pub struct TaskQueue {
    queue: VecDeque<Task>,
}

#[allow(dead_code)]
impl TaskQueue {
    pub fn new() -> Self {
        Self {
            queue: VecDeque::new(),
        }
    }

    pub fn add_task(&mut self, task: Task) {
        self.queue.push_back(task);
    }

    pub fn add_tasks(&mut self, tasks: Vec<Task>) {
        for task in tasks {
            self.add_task(task);
        }
    }

    pub fn pop(&mut self) -> Option<Task> {
        self.queue.pop_front()
    }

    pub fn len(&self) -> usize {
        self.queue.len()
    }

    pub fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }
}

impl Default for TaskQueue {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_id_generation() {
        let id = TaskId::new("nmap", "192.168.1.1", Some(80));
        assert!(id.0.contains("nmap"));
        assert!(id.0.contains("192_168_1_1"));
        assert!(id.0.contains("80"));
    }

    #[test]
    fn test_task_queue() {
        let mut queue = TaskQueue::new();
        assert!(queue.is_empty());

        let task = Task {
            id: TaskId::new("test", "127.0.0.1", None),
            tool_name: "test".to_string(),
            target: "127.0.0.1".to_string(),
            port: None,
            output_file: PathBuf::from("/tmp/test.json"),
            command: "test command".to_string(),
            timeout: Duration::from_secs(60),
        };

        queue.add_task(task.clone());
        assert_eq!(queue.len(), 1);

        let popped = queue.pop().unwrap();
        assert_eq!(popped.tool_name, "test");
        assert!(queue.is_empty());
    }
}
