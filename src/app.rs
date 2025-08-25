use crate::{
    core::{state::RunState, models::Target},
    organizers::{layout, audit},
    executors::toolchain,
    reporters::{writer, validate},
    ui::{
        printer,
        progress::{start_system_stats_task},
        events::UiEvent,
    },
    utils::{logging, time},
    config::ConfigLoader,
};
use anyhow::Result;

pub async fn run(cli: crate::cli::args::Cli) -> Result<()> {
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
    
    // Start the UI task (TUI or simple mode based on CLI flag)
    let ui_sender = crate::ui::progress::start_ui_task_with_options(cli.simple).await;
    
    // Start system stats monitoring
    let _stats_handle = start_system_stats_task(ui_sender.clone());
    
    // Generate run ID and prepare directories
    let run_id = time::new_run_id(&cli.target);
    tracing::info!("Run ID: {}", run_id);
    
    let dirs = layout::prepare_run_dirs(&run_id)?;
    
    // Run preflight checks unless skipped
    if !cli.skip_checks {
        audit::preflight_checks_with_config(&dirs, Some(&config))?;
    } else {
        tracing::warn!("Skipping preflight checks as requested");
    }
    
    // Verify tools are available
    toolchain::verify_or_bail()?;
    
    // Create target and state
    let target = Target::new(cli.target.clone(), run_id.clone(), dirs.clone())?;
    let mut state = RunState::new(&target, &dirs);
    
    // Connect state to UI sender for progress updates
    state.set_ui_sender(ui_sender.clone());
    
    // Execute scans with live monitoring
    crate::core::scheduler::execute_all_with_ui_sender(&mut state, &config, &ui_sender).await?;
    
    // Write reports
    writer::write_all(&state, &dirs, start_time)?;
    validate::validate_reports(&dirs)?;
    let _ = ui_sender.send(UiEvent::Shutdown);
    
    // Give UI time to shutdown cleanly
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    
    // Print final summary after UI is done
    printer::print_summary(&state);
    
    Ok(())
}
