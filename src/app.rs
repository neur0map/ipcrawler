use crate::{
    config::ConfigLoader,
    core::{models::Target, state::RunState},
    executors::toolchain,
    organizers::{audit, layout},
    reporters::{validate, writer},
    ui::{events::UiEvent, printer},
    utils::{logging, time},
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
    tracing::info!(
        "Configuration loaded with {} max scans, {} port scans",
        config.concurrency.max_total_scans,
        config.concurrency.max_port_scans
    );

    // Start the dashboard task
    let (ui_sender, _dashboard_enabled, dashboard_handle) =
        crate::dashboard::start_dashboard_task(cli.target.clone()).await;

    // Start system stats monitoring
    let _stats_handle = crate::monitoring::start_system_stats_task(ui_sender.clone());

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

    // Validate all plugins and their dependencies
    let registry = crate::core::scheduler::PluginRegistry::default().await;
    tracing::info!(
        "Validating {} plugins and their dependencies...",
        registry.total_plugins()
    );
    registry.validate_all_plugins()?;

    // Create target and state
    let target = Target::new(cli.target.clone(), run_id.clone(), dirs.clone())?;
    let mut state = RunState::new(&target, &dirs);

    // Connect state to UI sender for progress updates
    state.set_ui_sender(ui_sender.clone());

    // Execute scans with live monitoring
    crate::core::scheduler::execute_all_phases(&mut state, &registry, &config, &ui_sender).await?;

    // Write reports
    writer::write_all(&state, &dirs, start_time)?;
    validate::validate_reports(&dirs)?;

    // Notify UI that summary is ready
    let summary_path = dirs.report.join("summary.md");
    if summary_path.exists() {
        let _ = ui_sender.send(UiEvent::SummaryReady {
            file_path: summary_path,
        });
    }

    let _ = ui_sender.send(UiEvent::Shutdown);

    // Handle post-scan behavior
    if let Some(handle) = dashboard_handle {
        tracing::info!("Dashboard is running - press 'q' to quit");
        // Wait for dashboard to complete (user presses 'q')
        match handle.await {
            Ok(()) => {
                tracing::info!("Dashboard exited successfully");
            }
            Err(e) => {
                tracing::warn!("Dashboard task failed: {}", e);
            }
        }

        // Give a small delay to ensure clean exit
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    } else {
        tracing::info!("CLI mode was used, printing final summary");
        // Only print CLI summary when no dashboard was used
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        printer::print_summary(&state);
    }

    Ok(())
}
