use crate::{
    core::{state::RunState, models::Target},
    organizers::{layout, audit},
    executors::toolchain,
    reporters::{writer, validate},
    ui::{progress::ProgressManager, printer},
    utils::{logging, time},
    config::ConfigLoader,
};
use anyhow::Result;

pub fn run(cli: crate::cli::args::Cli) -> Result<()> {
    // Track start time for duration calculation
    let start_time = std::time::Instant::now();
    
    // Initialize logging
    let level = logging::level_from_cli(&cli);
    logging::init(level)?;
    
    tracing::info!("Starting ipcrawler for target: {}", cli.target);
    
    // Load configuration
    let config = ConfigLoader::load()?;
    tracing::info!("Configuration loaded with {} max scans, {} port scans", 
                  config.concurrency.max_total_scans, config.concurrency.max_port_scans);
    
    // Initialize progress UI
    let progress = ProgressManager::new();
    progress.update(&format!("Initializing scan for {}", cli.target));
    
    // Generate run ID and prepare directories
    let run_id = time::new_run_id(&cli.target);
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
    crate::core::scheduler::execute_all(&mut state, &config)?;
    
    // Write reports
    progress.update("Writing reports...");
    writer::write_all(&state, &dirs, start_time)?;
    validate::validate_reports(&dirs)?;
    
    // Complete progress and print summary
    progress.finish("Scan complete!");
    printer::print_summary(&state);
    
    Ok(())
}
