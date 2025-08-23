#!/usr/bin/env bash
set -euo pipefail

echo "=== Building ipcrawler Phases 4-8 ==="
echo "This script will create all remaining components for the ipcrawler project"
echo ""

# Phase 4: Scheduler with bounded concurrency
cat > src/core/scheduler.rs << 'EOF'
use std::sync::Arc;
use tokio::sync::Semaphore;
use anyhow::Result;
use super::{state::RunState, events::Event};

pub struct PluginRegistry {
    pub port_scans: Vec<Box<dyn crate::plugins::types::PortScan>>,
    pub service_scans: Vec<Box<dyn crate::plugins::types::ServiceScan>>,
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self {
            port_scans: vec![
                Box::new(crate::plugins::portscan_nmap::NmapPortScan),
            ],
            service_scans: vec![
                Box::new(crate::plugins::http_probe::HttpProbe),
            ],
        }
    }
}

pub async fn execute_all_async(state: &mut RunState, registry: &PluginRegistry) -> Result<()> {
    let max_scans: usize = 50;
    let max_ports: usize = 10;
    let sem_ports = Arc::new(Semaphore::new(max_ports));
    let sem_svcs = Arc::new(Semaphore::new(max_scans - max_ports));

    // Port scans
    let mut discovered = vec![];
    for p in &registry.port_scans {
        let _permit = sem_ports.acquire().await?;
        state.on_event(Event::TaskStarted(p.name()));
        match p.run(state).await {
            Ok(mut svcs) => {
                for svc in &svcs {
                    state.on_event(Event::ServiceDiscovered(svc.clone()));
                }
                discovered.append(&mut svcs);
                state.on_event(Event::TaskCompleted(p.name()));
            }
            Err(e) => {
                tracing::error!("Port scan failed: {}", e);
                return Err(e);
            }
        }
    }

    // Service scans
    for s in discovered.iter() {
        for plg in &registry.service_scans {
            if !plg.matches(s) { continue; }
            let _permit = sem_svcs.acquire().await?;
            state.on_event(Event::TaskStarted(plg.name()));
            if let Err(e) = plg.run(s, state).await {
                tracing::error!("Service scan failed: {}", e);
                return Err(e);
            }
            state.on_event(Event::TaskCompleted(plg.name()));
        }
    }

    Ok(())
}

pub fn execute_all(state: &mut RunState) -> Result<()> {
    let registry = PluginRegistry::default();
    tokio::runtime::Runtime::new()?.block_on(execute_all_async(state, &registry))
}
EOF

# Phase 5: Plugin system
cat > src/plugins/types.rs << 'EOF'
use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::RunState};

#[async_trait]
pub trait PortScan: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run(&self, state: &RunState) -> Result<Vec<Service>>;
}

#[async_trait]
pub trait ServiceScan: Send + Sync {
    fn name(&self) -> &'static str;
    fn matches(&self, service: &Service) -> bool;
    async fn run(&self, service: &Service, state: &RunState) -> Result<()>;
}

#[async_trait]
pub trait Report: Send + Sync {
    fn name(&self) -> &'static str;
    async fn generate(&self, state: &RunState) -> Result<()>;
}
EOF

cat > src/plugins/portscan_nmap.rs << 'EOF'
use async_trait::async_trait;
use anyhow::Result;
use regex::Regex;
use std::path::PathBuf;
use crate::core::{models::{Service, Proto}, state::RunState};
use crate::executors::command::execute;

pub struct NmapPortScan;

#[async_trait]
impl crate::plugins::types::PortScan for NmapPortScan {
    fn name(&self) -> &'static str {
        "nmap_portscan"
    }

    async fn run(&self, state: &RunState) -> Result<Vec<Service>> {
        let target = &state.target;
        let dirs = state.dirs.as_ref().unwrap();
        let output_file = dirs.scans.join("nmap.xml");
        
        let args = vec![
            "-sS",
            "-sV",
            "-T4",
            "-oX", output_file.to_str().unwrap(),
            target,
        ];
        
        let result = execute("nmap", &args, &dirs.scans, Some(300000)).await?;
        
        // Parse XML output
        let xml_content = std::fs::read_to_string(&output_file)?;
        parse_nmap_xml(&xml_content, target)
    }
}

fn parse_nmap_xml(xml: &str, target: &str) -> Result<Vec<Service>> {
    let mut services = Vec::new();
    
    // Simple regex-based parsing for demonstration
    let port_re = Regex::new(r#"<port protocol="(\w+)" portid="(\d+)".*?<state state="open".*?<service name="([^"]+)".*?/>"#)?;
    
    for cap in port_re.captures_iter(xml) {
        let proto = match &cap[1] {
            "tcp" => Proto::Tcp,
            "udp" => Proto::Udp,
            _ => continue,
        };
        
        let port: u16 = cap[2].parse()?;
        let name = cap[3].to_string();
        let secure = name.ends_with("s") || name.contains("ssl") || name.contains("tls");
        
        services.push(Service {
            proto,
            port,
            name,
            secure,
            address: target.to_string(),
        });
    }
    
    Ok(services)
}
EOF

cat > src/plugins/http_probe.rs << 'EOF'
use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::RunState};
use crate::executors::command::execute;

pub struct HttpProbe;

#[async_trait]
impl crate::plugins::types::ServiceScan for HttpProbe {
    fn name(&self) -> &'static str {
        "http_probe"
    }

    fn matches(&self, service: &Service) -> bool {
        service.name.contains("http") || 
        service.port == 80 || 
        service.port == 443 ||
        service.port == 8080 ||
        service.port == 8443
    }

    async fn run(&self, service: &Service, state: &RunState) -> Result<()> {
        let dirs = state.dirs.as_ref().unwrap();
        let scheme = if service.secure || service.port == 443 { "https" } else { "http" };
        let url = format!("{}://{}:{}", scheme, service.address, service.port);
        let output_file = dirs.scans.join(format!("http_{}_{}.txt", service.address, service.port));
        
        let args = vec![
            "-s",
            "-L",
            "-m", "10",
            "-I",
            "-o", output_file.to_str().unwrap(),
            &url,
        ];
        
        match execute("curl", &args, &dirs.scans, Some(15000)).await {
            Ok(_) => {
                tracing::info!("HTTP probe successful for {}", url);
            }
            Err(e) => {
                tracing::warn!("HTTP probe failed for {}: {}", url, e);
            }
        }
        
        Ok(())
    }
}
EOF

cat > src/plugins/mod.rs << 'EOF'
pub mod types;
pub mod portscan_nmap;
pub mod http_probe;
EOF

# Phase 6: Reporters
cat > src/reporters/writer.rs << 'EOF'
use anyhow::Result;
use serde_json;
use std::fs;
use crate::core::{state::RunState, models::RunDirs};
use crate::utils::fs::atomic_write;

pub fn write_all(state: &RunState, dirs: &RunDirs) -> Result<()> {
    write_text_summary(state, dirs)?;
    write_json_summary(state, dirs)?;
    Ok(())
}

fn write_text_summary(state: &RunState, dirs: &RunDirs) -> Result<()> {
    let path = dirs.report.join("summary.txt");
    let content = format!(
        "=== ipcrawler Run Summary ===\n\
        Target: {}\n\
        Run ID: {}\n\
        \n\
        Open Ports: {}\n\
        Services Discovered: {}\n\
        Tasks Completed: {}/{}\n\
        Errors: {}\n\
        \n\
        Ports:\n{}\n\
        \n\
        Services:\n{}\n",
        state.target,
        state.run_id,
        state.ports_open.len(),
        state.services.len(),
        state.tasks_completed,
        state.tasks_started,
        state.errors.len(),
        format_ports(&state.ports_open),
        format_services(&state.services)
    );
    
    atomic_write(path, content.as_bytes())?;
    Ok(())
}

fn write_json_summary(state: &RunState, dirs: &RunDirs) -> Result<()> {
    let path = dirs.report.join("summary.json");
    let json = serde_json::to_string_pretty(state)?;
    atomic_write(path, json.as_bytes())?;
    Ok(())
}

fn format_ports(ports: &[(u16, String)]) -> String {
    if ports.is_empty() {
        return "  None".to_string();
    }
    ports.iter()
        .map(|(p, n)| format!("  - {}: {}", p, n))
        .collect::<Vec<_>>()
        .join("\n")
}

fn format_services(services: &[crate::core::models::Service]) -> String {
    if services.is_empty() {
        return "  None".to_string();
    }
    services.iter()
        .map(|s| format!("  - {}:{}/{:?} ({})", s.address, s.port, s.proto, s.name))
        .collect::<Vec<_>>()
        .join("\n")
}
EOF

cat > src/reporters/validate.rs << 'EOF'
use anyhow::{Result, bail};
use std::fs;
use crate::core::models::RunDirs;

pub fn validate_reports(dirs: &RunDirs) -> Result<()> {
    let required_files = vec![
        dirs.report.join("summary.txt"),
        dirs.report.join("summary.json"),
    ];
    
    for file in required_files {
        if !file.exists() {
            bail!("Required report file missing: {:?}", file);
        }
        
        let metadata = fs::metadata(&file)?;
        if metadata.len() == 0 {
            bail!("Report file is empty: {:?}", file);
        }
    }
    
    tracing::info!("All reports validated successfully");
    Ok(())
}
EOF

cat > src/reporters/mod.rs << 'EOF'
pub mod writer;
pub mod validate;
EOF

# Phase 7: UI
cat > src/ui/progress.rs << 'EOF'
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::time::Duration;

pub struct ProgressManager {
    multi: MultiProgress,
    main_bar: ProgressBar,
}

impl ProgressManager {
    pub fn new() -> Self {
        let multi = MultiProgress::new();
        let main_bar = multi.add(ProgressBar::new_spinner());
        
        main_bar.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.green} {msg}")
                .unwrap()
                .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈ ")
        );
        
        main_bar.enable_steady_tick(Duration::from_millis(100));
        
        Self { multi, main_bar }
    }
    
    pub fn update(&self, msg: &str) {
        self.main_bar.set_message(msg.to_string());
    }
    
    pub fn finish(&self, msg: &str) {
        self.main_bar.finish_with_message(msg.to_string());
    }
}
EOF

cat > src/ui/printer.rs << 'EOF'
use crate::core::state::RunState;
use yansi::Paint;

pub fn print_summary(state: &RunState) {
    println!("\n{}", Paint::green("═══════════════════════════════════════").bold());
    println!("{}", Paint::green("ipcrawler Run Complete").bold());
    println!("{}", Paint::green("═══════════════════════════════════════").bold());
    
    println!("\n{}: {}", Paint::cyan("Target").bold(), state.target);
    println!("{}: {}", Paint::cyan("Run ID").bold(), state.run_id);
    
    println!("\n{}", Paint::yellow("Results:").bold());
    println!("  Open Ports: {}", Paint::green(state.ports_open.len().to_string()).bold());
    println!("  Services: {}", Paint::green(state.services.len().to_string()).bold());
    
    println!("\n{}", Paint::yellow("Execution:").bold());
    println!("  Tasks: {}/{}", 
        Paint::green(state.tasks_completed.to_string()).bold(),
        state.tasks_started
    );
    
    if !state.errors.is_empty() {
        println!("  Errors: {}", Paint::red(state.errors.len().to_string()).bold());
    }
    
    if !state.ports_open.is_empty() {
        println!("\n{}", Paint::yellow("Open Ports:").bold());
        for (port, service) in &state.ports_open {
            println!("  • {}: {}", Paint::cyan(port.to_string()), service);
        }
    }
    
    println!("\n{}", Paint::green("Reports written to artifacts/runs/").dim());
}
EOF

cat > src/ui/mod.rs << 'EOF'
pub mod progress;
pub mod printer;
EOF

# Update app.rs for all phases
cat > src/app.rs << 'EOF'
use crate::{
    core::{state::RunState, models::Target},
    organizers::{layout, audit},
    executors::toolchain,
    reporters::{writer, validate},
    ui::{progress::ProgressManager, printer},
    utils::{logging, time},
};
use anyhow::Result;

pub fn run(cli: crate::cli::args::Cli) -> Result<()> {
    // Initialize logging
    let level = logging::level_from_cli(&cli);
    logging::init(level)?;
    
    tracing::info!("Starting ipcrawler for target: {}", cli.target);
    
    // Initialize progress UI
    let progress = ProgressManager::new();
    progress.update(&format!("Initializing scan for {}", cli.target));
    
    // Generate run ID and prepare directories
    let run_id = time::new_run_id();
    tracing::info!("Run ID: {}", run_id);
    
    progress.update("Preparing run directories...");
    let dirs = layout::prepare_run_dirs(&run_id)?;
    audit::preflight_checks(&dirs)?;
    
    // Verify tools are available
    progress.update("Verifying tools...");
    toolchain::verify_or_bail()?;
    
    // Create target and state
    let target = Target::new(cli.target.clone(), run_id.clone(), dirs.clone())?;
    let mut state = RunState::new(&target, &dirs);
    
    // Execute scans
    progress.update("Executing scans...");
    crate::core::scheduler::execute_all(&mut state)?;
    
    // Write reports
    progress.update("Writing reports...");
    writer::write_all(&state, &dirs)?;
    validate::validate_reports(&dirs)?;
    
    // Complete progress and print summary
    progress.finish("Scan complete!");
    printer::print_summary(&state);
    
    Ok(())
}
EOF

# Update main.rs to include all modules
cat > src/main.rs << 'EOF'
mod app;
mod cli;
mod core;
mod executors;
mod organizers;
mod plugins;
mod reporters;
mod ui;
mod utils;

use clap::Parser;

fn main() {
    let cli = cli::args::Cli::parse();
    if let Err(err) = app::run(cli) {
        eprintln!("fatal: {:#}", err);
        std::process::exit(1);
    }
}
EOF

echo "=== Phase 4-8 files created successfully ==="
echo ""
echo "Building the complete project..."
cargo build --release 2>&1 | tail -5

echo ""
echo "=== Build complete! ==="
echo "Run with: make run RUN_ARGS=\"-t scanme.nmap.org -v\""