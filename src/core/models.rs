use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug)]
pub struct RunDirs {
    pub root: PathBuf,    // artifacts/runs/<id>
    pub scans: PathBuf,
    pub loot: PathBuf,
    pub report: PathBuf,
    pub logs: PathBuf,
}

#[derive(Clone, Debug)]
pub struct Target {
    pub value: String,    // host/IP/domain
    pub run_id: String,
    #[allow(dead_code)]
    pub dirs: RunDirs,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum Proto { 
    Tcp, 
    Udp 
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Service {
    pub proto: Proto,
    pub port: u16,
    pub name: String,     // e.g., "http", "ssh"
    pub secure: bool,     // e.g., https
    pub address: String,  // normalized host/IP
}

impl Target {
    pub fn new(value: String, run_id: String, dirs: RunDirs) -> anyhow::Result<Self> {
        Ok(Self { value, run_id, dirs })
    }
}