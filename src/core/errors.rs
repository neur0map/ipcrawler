use thiserror::Error;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecError {
    pub tool: String,
    pub args: Vec<String>,
    pub cwd: String,
    pub exit_code: Option<i32>,
    pub stderr_tail: String,
    pub duration_ms: u128,
}

#[derive(Error, Debug)]
pub enum IpcrawlerError {
    #[error("execution failed: {0:?}")]
    Exec(ExecError),
    
    #[error("report failure: {0}")]
    #[allow(dead_code)]
    Report(String),
    
    #[error("organizer failure: {0}")]
    #[allow(dead_code)]
    Organizer(String),
    
    #[error("dependency missing: {0}")]
    #[allow(dead_code)]
    Dependency(String),
    
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("general error: {0}")]
    #[allow(dead_code)]
    Other(String),
}