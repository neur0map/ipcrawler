mod cli;
mod config;
mod doctor;
mod error_handler;
mod executor;
mod gradient;
mod help;
mod output;
mod parser;
mod paths;
mod pipeline;
mod progress;
mod table;
mod template;
mod validator;

use crate::gradient::gradient_path;
use chrono::Local;
use clap::Parser;
use colored::*;
use config::Config;
use doctor::DependencyChecker;
use executor::{ExecutionContext, Executor};
#[cfg(feature = "notify-rust")]
use notify_rust::Notification;
use output::ReportGenerator;
use paths::ReconPaths;
use pipeline::Pipeline;
use progress::ProgressManager;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Arc;

async fn execute_single_config(
    config: Config,
    context: ExecutionContext,
    config_name: String,
    progress_manager: Arc<ProgressManager>,
    emergency_stop: bool,
    notifications: bool,
) -> Result<Vec<executor::ToolResult>, Box<dyn std::error::Error + Send + Sync>> {
    // Decide whether to use chaining or simple execution
    let has_chains = !config.chains.is_empty();

    if has_chains {
        let mut pipeline = Pipeline::new(
            config,
            context,
            progress_manager.clone(),
            emergency_stop,
            notifications,
        );
        match pipeline.execute_with_chaining().await {
            Ok(res) => Ok(res),
            Err(e) => Err(format!("Pipeline failed for {}: {}", config_name, e).into()),
        }
    } else {
        let mut executor = match Executor::new(
            config,
            context,
            progress_manager,
            emergency_stop,
            notifications,
        ) {
            Ok(exec) => exec,
            Err(e) => {
                return Err(format!("Failed to create executor for {}: {}", config_name, e).into());
            }
        };

        match executor.execute_all().await {
            Ok(res) => {
                executor.print_summary(&res);
                Ok(res)
            }
            Err(e) => Err(format!("Execution failed for {}: {}", config_name, e).into()),
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Setup human-panic for better error reporting
    human_panic::setup_panic!();

    // Initialize path resolution system early for context detection
    let paths = ReconPaths::new()?;

    // Check for help flags before parsing to detect long vs short help
    let raw_args: Vec<String> = std::env::args().collect();
    let is_long_help = raw_args.contains(&"--help".to_string());

    let args = cli::Cli::parse();

    // Handle help and version flags
    if args.help {
        help::HelpDisplay::show_help(is_long_help);
    }

    if args.version {
        let version = env!("CARGO_PKG_VERSION");
        // Version shows context based on where it's running, not build features
        let context = if std::env::current_dir()
            .map(|d| d.join("Cargo.toml").exists())
            .unwrap_or(false)
        {
            "+dev"
        } else {
            ""
        };

        println!("ipcrawler {}{}", version, context);
        std::process::exit(0);
    }

    // Initialize modern progress management system early
    let progress = Arc::new(ProgressManager::new());

    paths.ensure_user_dirs()?;

    // If --paths flag is set, show directory information and exit
    if args.paths {
        print_path_info(&paths, &args);
        return Ok(());
    }

    // Handle profile override and multiple configs
    let config_names = if let Some(profile) = &args.profile {
        vec![profile.clone()]
    } else {
        args.config.clone()
    };

    // Resolve all configuration paths
    let mut config_paths = Vec::new();
    for config_name in &config_names {
        match paths.resolve_config(config_name) {
            Ok(path) => config_paths.push(path),
            Err(e) => {
                progress.print_error(&e.to_string());
                progress.print_info("Available configs:");
                for (name, path) in paths.list_available_configs() {
                    progress.print_info(&format!("  - {} -> {}", name, path.display()));
                }
                std::process::exit(1);
            }
        }
    }

    // Load and validate all configurations
    let mut configs = Vec::new();
    for config_path in &config_paths {
        match Config::from_file(config_path) {
            Ok(cfg) => {
                if args.verbose || args.validate {
                    progress.print_success(&format!(
                        "Configuration loaded from: {}",
                        gradient_path(&config_path.display().to_string())
                    ));
                }
                configs.push(cfg);
            }
            Err(e) => {
                progress.print_error(&format!(
                    "Failed to load configuration {}: {}",
                    gradient_path(&config_path.display().to_string()),
                    e
                ));
                return Err(e);
            }
        }
    }

    // If --update flag is set, update ipcrawler and exit
    if args.update {
        return handle_update().await;
    }

    // If --list flag is set, list all available configurations and exit
    if args.list {
        return handle_list_configs(&paths).await;
    }

    // If --doctor flag is set, check system dependencies and exit
    if args.doctor {
        let dependency_checker = DependencyChecker::new();
        for config in &configs {
            dependency_checker.print_doctor_report(config);
        }
        return Ok(());
    }

    // If --list-tools flag is set, show available tools and exit
    if args.list_tools {
        for (i, config) in configs.iter().enumerate() {
            if configs.len() > 1 {
                progress.print_section(&format!("Config {}: {}", i + 1, config_names[i]));
            }
            print_tools_info(config);
        }
        return Ok(());
    }

    // If --validate flag is set, validate and exit
    if args.validate {
        for (i, config) in configs.iter().enumerate() {
            if configs.len() > 1 {
                progress.print_section(&format!("Config {}: {}", i + 1, config_names[i]));
            }
            progress.print_success("Configuration is valid!");
            config.print_summary();
        }
        return Ok(());
    }

    // Handle --resume flag
    if let Some(resume_dir) = &args.resume {
        return handle_resume_scan(resume_dir, &paths, &args).await;
    }

    // Extract target (guaranteed to exist if not in validate/list-tools/resume mode)
    let target = args.target.as_ref().unwrap();

    // Use smart output directory resolution
    let output_base = if let Some(custom_path) = &args.output {
        // User provided custom output path
        if args.debug {
            progress.print_info(&format!(
                "Using custom output path: {}",
                custom_path.display()
            ));
        }
        custom_path.clone()
    } else {
        // Use default output directory (production-aware)
        let default_dir = paths.default_output_dir();
        if args.debug {
            let mode = if paths.development_output_dir() == default_dir {
                "development"
            } else {
                "production"
            };
            progress.print_info(&format!(
                "Using default output path ({}): {}",
                mode,
                default_dir.display()
            ));
        }
        default_dir
    };

    if args.verbose {
        progress.print_info(&format!("Target: {}", target));
        progress.print_info(&format!("Configs: {}", config_names.join(", ")));
        progress.print_info(&format!("Base output directory: {}", output_base.display()));
    }

    let output_dir = create_output_structure(target, &output_base)?;

    if args.verbose {
        progress.print_info(&format!("Results -> {}", output_dir.display()));
    }

    // Create report generator
    let mut report_generator =
        ReportGenerator::new(target.clone(), output_dir.clone(), config_names.join(","));

    // Replace template variables in all configs
    for config in &mut configs {
        config.replace_variables(target, &output_dir.to_string_lossy());
    }

    // Validate configurations with enhanced validation
    for config in configs.iter() {
        if let Err(e) = config.validate() {
            return Err(e);
        }

        // TODO: Additional runtime validation when ConfigValidator is fully implemented
        // if let Err(e) = validator::ConfigValidator::validate_config(config) {
        //     progress.print_error(&format!("Configuration validation failed: {}", e));
        //     return Err(Box::new(e));
        // }
    }

    // Verify output directory structure (instant)
    if !output_base.exists() {
        fs::create_dir_all(&output_base)?;
    }

    if args.verbose {
        for (i, config) in configs.iter().enumerate() {
            if configs.len() > 1 {
                progress.print_section(&format!("Config {}: {}", i + 1, config_names[i]));
            }
            config.print_summary();
        }

        // Show execution plan in verbose mode
        if args.verbose {
            progress.print_section("Execution Plan");
            progress.print_info(&format!("  Total configs: {}", configs.len()));
            let _total_tools: usize = configs
                .iter()
                .map(|c| c.tools.iter().filter(|t| t.enabled).count())
                .sum();
            progress.print_info(&format!("  Total enabled tools: {}", _total_tools));
            let _has_chains = configs.iter().any(|c| !c.chains.is_empty());
            progress.print_info(&format!(
                "  Execution mode: {}",
                if _has_chains { "chained" } else { "parallel" }
            ));
            progress.print_info(&format!("  Output directory: {}", output_dir.display()));
        }
    }

    // Create execution context
    let _context = ExecutionContext {
        output_dir: output_dir.clone(),
        target: target.clone(),
        debug: args.debug,
        verbose: args.verbose,
    };

    // Handle --dry-run flag early to avoid unused context warning
    if args.dry_run {
        for (i, config) in configs.iter().enumerate() {
            if configs.len() > 1 {
                progress.print_section(&format!("Config {}: {}", i + 1, config_names[i]));
            }
            print_dry_run_info(config, target, &output_dir, &progress);
        }
        progress.finish();
        return Ok(());
    }

    // Execute all configs in parallel

    let mut all_results = Vec::new();
    let mut tasks = Vec::new();

    for (i, config) in configs.into_iter().enumerate() {
        let context_clone = ExecutionContext {
            output_dir: output_dir.clone(),
            target: target.clone(),
            debug: args.debug,
            verbose: args.verbose,
        };
        let config_name = config_names[i].clone();
        let progress_clone = progress.clone();

        // Create a future for each config execution
        let emergency_stop = !args.no_emergency_stop;
        let notifications = !args.no_notifications;
        let task = tokio::spawn(async move {
            execute_single_config(
                config,
                context_clone,
                config_name,
                progress_clone,
                emergency_stop,
                notifications,
            )
            .await
        });

        tasks.push(task);
    }

    // Wait for all tasks to complete
    for (i, task) in tasks.into_iter().enumerate() {
        match task.await {
            Ok(Ok(results)) => {
                progress.print_success(&format!("{} completed", config_names[i]));
                all_results.extend(results);
            }
            Ok(Err(e)) => {
                progress.print_error(&format!("{} failed: {}", config_names[i], e));
            }
            Err(e) => {
                progress.print_error(&format!("{} panicked: {}", config_names[i], e));
            }
        }
    }

    let results = all_results;

    // Print final summary
    if !results.is_empty() {
        print_chain_summary(&results, &progress, args.verbose);
    }

    // Generate summary reports in multiple formats
    if !results.is_empty() {
        if let Ok(summary) = report_generator.generate_summary_report(&results) {
            // Generate all report formats using the new templating system
            let formats = [
                (template::OutputFormat::Json, "JSON"),
                (template::OutputFormat::Html, "HTML"),
                (template::OutputFormat::Text, "Text"),
                (template::OutputFormat::Markdown, "Markdown"),
            ];

            for (format, name) in formats {
                if let Ok(report_path) = report_generator.save_report(&summary, format) {
                    if args.verbose {
                        progress.print_info(&format!(
                            "{} report -> {}",
                            name,
                            report_path.display()
                        ));
                    }
                }
            }
        }
    }

    progress.print_success("Scan complete");

    // Display beautiful tables in verbose mode
    if args.verbose && !results.is_empty() {
        if let Ok(summary) = report_generator.generate_summary_report(&results) {
            progress.print_section("📊 Scan Summary");

            // Collect discoveries by type (following anti-hardcoding rules)
            // Use HashSet to automatically deduplicate
            let mut ports_set = std::collections::HashSet::new();
            let mut services_set = std::collections::HashSet::new();
            let mut vulns_set = std::collections::HashSet::new();

            for discovery in &summary.discoveries {
                match &discovery.discovery_type {
                    crate::output::DiscoveryType::Port { number, protocol } => {
                        ports_set.insert(format!("{}/{}", number, protocol));
                    }
                    crate::output::DiscoveryType::Service {
                        port,
                        protocol,
                        name,
                        version,
                    } => {
                        let service_str = if let Some(ver) = version {
                            format!("{} {}/{} ({})", name, port, protocol, ver)
                        } else {
                            format!("{} {}/{}", name, port, protocol)
                        };
                        services_set.insert(service_str);
                    }
                    crate::output::DiscoveryType::Vulnerability { severity, cve } => {
                        let vuln_str = if let Some(cve_id) = cve {
                            format!("{} ({})", severity, cve_id)
                        } else {
                            severity.clone()
                        };
                        vulns_set.insert(vuln_str);
                    }
                    _ => {
                        // Handle other discovery types generically
                        // This follows the anti-hardcoding rules
                    }
                }
            }

            // Convert to sorted vectors for consistent display
            let mut ports: Vec<String> = ports_set.into_iter().collect();
            let mut services: Vec<String> = services_set.into_iter().collect();
            let mut vulns: Vec<String> = vulns_set.into_iter().collect();

            // Sort for consistent display
            ports.sort();
            services.sort();
            vulns.sort();

            // Print beautiful discovery table (only in verbose mode)
            if args.verbose {
                println!(
                    "{}",
                    table::TableBuilder::discovery_summary(&ports, &services, &vulns)
                );

                // Tool execution summary
                println!("\n📈 Tool Execution Report");
                println!("{}", table::TableBuilder::tool_execution_summary(&results));
            }
        }
    }

    // Show where results are stored - mode is determined by path context, not build features
    let mode = if paths.is_dev_context() {
        "Development"
    } else {
        "Production"
    };

    progress.print_section("📁 Results Location");
    progress.print_info(&format!("Mode: {} Mode", mode));
    progress.print_info(&format!("Path: {}", output_dir.display()));

    // List generated reports
    let report_files = [
        "scan_summary.json",
        "scan_summary.html",
        "scan_summary.md",
        "scan_summary.txt",
    ];

    progress.print_info("Generated Reports:");
    for report in &report_files {
        let report_path = output_dir.join(report);
        if report_path.exists() {
            progress.print_info(&format!("  • {} -> {}", report, report_path.display()));
        }
    }

    // Interactive markdown summary viewing with 'see' integration
    let markdown_summary = output_dir.join("scan_summary.md");
    if markdown_summary.exists() {
        let doctor = doctor::DependencyChecker::new();
        if doctor.is_see_available() {
            println!(); // Add spacing before prompt

            if progress.prompt_user_yn("Do you want to view the markdown summary?", false) {
                progress.print_info("Opening markdown summary in new terminal window...");

                // Detect OS and launch 'see' in new terminal window with 130x60 size
                let success = if cfg!(target_os = "macos") {
                    // macOS: Use osascript to open new Terminal window
                    std::process::Command::new("osascript")
                        .arg("-e")
                        .arg(&format!(
                            "tell application \"Terminal\" to do script \"see --show-line-numbers=true '{}'; read -p 'Press Enter to close...'\"",
                            markdown_summary.display()
                        ))
                        .arg("-e")
                        .arg("tell application \"Terminal\" to set bounds of front window to {100, 100, 1400, 800}")
                        .status()
                        .map(|status| status.success())
                        .unwrap_or(false)
                } else if cfg!(target_os = "linux") {
                    // Linux: Try different terminal emulators
                    if std::process::Command::new("which")
                        .arg("gnome-terminal")
                        .output()
                        .map(|o| o.status.success())
                        .unwrap_or(false)
                    {
                        std::process::Command::new("gnome-terminal")
                            .arg("--geometry=130x60")
                            .arg("--")
                            .arg("bash")
                            .arg("-c")
                            .arg(&format!("see --show-line-numbers=true '{}'; read -p 'Press Enter to close...'", markdown_summary.display()))
                            .spawn()
                            .is_ok()
                    } else if std::process::Command::new("which")
                        .arg("xterm")
                        .output()
                        .map(|o| o.status.success())
                        .unwrap_or(false)
                    {
                        std::process::Command::new("xterm")
                            .arg("-geometry")
                            .arg("130x60")
                            .arg("-e")
                            .arg("bash")
                            .arg("-c")
                            .arg(&format!("see --show-line-numbers=true '{}'; read -p 'Press Enter to close...'", markdown_summary.display()))
                            .spawn()
                            .is_ok()
                    } else {
                        // Fallback to current terminal
                        std::process::Command::new("see")
                            .arg("--show-line-numbers=true")
                            .arg(&markdown_summary)
                            .status()
                            .map(|status| status.success())
                            .unwrap_or(false)
                    }
                } else {
                    // Windows or other OS: fallback to current terminal
                    std::process::Command::new("see")
                        .arg("--show-line-numbers=true")
                        .arg(&markdown_summary)
                        .status()
                        .map(|status| status.success())
                        .unwrap_or(false)
                };

                if success {
                    if cfg!(target_os = "macos") || cfg!(target_os = "linux") {
                        progress.print_success(
                            "Markdown summary opened in new terminal window (130x60)",
                        );
                    } else {
                        progress.print_success("Markdown summary viewed successfully");
                    }
                } else {
                    progress.print_warning("Failed to open new terminal window, falling back...");

                    // Fallback to current terminal
                    match std::process::Command::new("see")
                        .arg("--show-line-numbers=true")
                        .arg(&markdown_summary)
                        .status()
                    {
                        Ok(status) if status.success() => {
                            progress.print_success("Markdown summary viewed in current terminal");
                        }
                        Ok(_) => {
                            progress.print_warning("'see' exited with non-zero status");
                        }
                        Err(e) => {
                            progress.print_error(&format!("Failed to launch 'see': {}", e));
                            progress.print_info(&format!(
                                "You can manually view: {}",
                                markdown_summary.display()
                            ));
                        }
                    }
                }
            }
        } else if args.verbose {
            progress.print_info("💡 Tip: Install 'see' for interactive markdown viewing:");
            progress.print_info("  cargo install see-cat");
        }
    }

    // Ensure all progress bars are properly cleaned up
    progress.finish();

    if args.debug {
        progress.print_section("Debug Information");
        progress.print_info(&format!("  Target: {}", target));
        progress.print_info(&format!("  Config Files: {}", config_names.join(", ")));
        progress.print_info(&format!("  Output Directory: {}", output_dir.display()));
        progress.print_info(&format!(
            "  Debug Mode: {}",
            if args.debug { "Enabled" } else { "Disabled" }
        ));
        progress.print_info(&format!(
            "  Verbose Mode: {}",
            if args.verbose { "Enabled" } else { "Disabled" }
        ));
        progress.print_info(&format!("  Tools executed: {}", results.len()));
        progress.print_info(&format!(
            "  Total duration: {:.2}s",
            results
                .iter()
                .map(|r| r.duration)
                .sum::<std::time::Duration>()
                .as_secs_f64()
        ));
    }

    Ok(())
}

fn create_output_structure(
    target: &str,
    base_dir: &PathBuf,
) -> Result<PathBuf, Box<dyn std::error::Error>> {
    let dir_timestamp = Local::now().format("%Y-%m-%d_%H-%M-%S").to_string();
    let dir_name = format!("{}_{}", target.replace(['/', ':', '.'], "_"), dir_timestamp);
    let output_path = base_dir.join(dir_name);

    fs::create_dir_all(&output_path)?;
    fs::create_dir_all(output_path.join("logs"))?;
    fs::create_dir_all(output_path.join("raw"))?;
    fs::create_dir_all(output_path.join("errors"))?;

    let log_file = output_path.join("logs").join("execution.log");
    let mut file = fs::File::create(&log_file)?;
    writeln!(
        file,
        "[{}] Scan initialized for target: {}",
        timestamp(),
        target
    )?;
    writeln!(
        file,
        "[{}] Output directory: {}",
        timestamp(),
        output_path.display()
    )?;

    Ok(output_path)
}

fn timestamp() -> String {
    Local::now().format("%Y-%m-%d %H:%M:%S").to_string()
}

// Print functions removed - using ProgressManager instead

fn print_chain_summary(
    results: &[executor::ToolResult],
    progress: &ProgressManager,
    verbose: bool,
) {
    if verbose {
        progress.print_section("Execution Summary");

        let successful: Vec<_> = results.iter().filter(|r| r.exit_code == 0).collect();
        let failed: Vec<_> = results.iter().filter(|r| r.exit_code != 0).collect();

        if !successful.is_empty() {
            progress.print_success(&format!("Successful ({})", successful.len()));
            for result in successful {
                let duration_str = format!("{:.2}s", result.duration.as_secs_f64());
                progress.print_info(&format!("    {} ({})", result.tool_name, duration_str));
            }
        }

        if !failed.is_empty() {
            progress.print_error(&format!("Failed ({})", failed.len()));
            for result in failed {
                progress.print_error(&format!(
                    "    {} (exit code: {})",
                    result.tool_name, result.exit_code
                ));
                if let Some(ref error) = result.error {
                    progress.print_error(&format!("      {}", error));
                }
            }
        }

        let total_duration: std::time::Duration = results.iter().map(|r| r.duration).sum();
        progress.print_info(&format!(
            "Total execution time: {:.2}s",
            total_duration.as_secs_f64()
        ));
    }
}

fn print_path_info(paths: &ReconPaths, args: &cli::Cli) {
    use std::os::unix::fs::MetadataExt;

    println!(
        "{}",
        "[PATHS] Directory Paths Information".bright_cyan().bold()
    );
    println!();

    // System Information
    println!("{}", "[SYSTEM] System Information:".bright_blue());
    println!("   Platform: {}", std::env::consts::OS);
    println!("   Architecture: {}", std::env::consts::ARCH);
    if let Ok(user) = std::env::var("USER") {
        println!("   User: {}", user);
    }
    println!();

    // Binary Location
    println!("{}", "[BINARY] Binary Location:".bright_green());
    if let Ok(exe_path) = std::env::current_exe() {
        println!(
            "   Executable: {}",
            exe_path.display().to_string().bright_white()
        );
        if let Ok(metadata) = std::fs::metadata(&exe_path) {
            let size_kb = metadata.size() / 1024;
            println!("   Size: {} KB", size_kb.to_string().bright_black());
        }
    }
    println!();

    // Configuration Directories
    println!("{}", "[CONFIG] Configuration Directories:".bright_yellow());

    // Working directory
    println!(
        "   {} {}",
        "Working Directory:".bright_white(),
        gradient_path(&paths.working_dir.display().to_string())
    );
    println!("     Purpose: Project-specific configs and current output");
    if paths.working_dir.join("config").exists() {
        println!(
            "     Status: {} (contains system templates)",
            "[ACTIVE]".green()
        );
    } else {
        println!("     Status: {} (no local configs)", "[EMPTY]".yellow());
    }
    println!();

    // User config directory
    println!(
        "   {} {}",
        "User Config Directory:".bright_white(),
        gradient_path(&paths.user_config.display().to_string())
    );
    println!("     Purpose: Personal profiles and user-specific configurations");
    let profiles_dir = paths.user_config.join("profiles");
    if profiles_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&profiles_dir) {
            let count = entries.count();
            println!(
                "     Status: {} ({} user profiles)",
                "[ACTIVE]".green(),
                count
            );
        } else {
            println!(
                "     Status: {} (directory exists but unreadable)",
                "[WARNING]".yellow()
            );
        }
    } else {
        println!(
            "     Status: {} (will be created when needed)",
            "[NOT_CREATED]".yellow()
        );
    }
    println!();

    // User data directory
    println!(
        "   {} {}",
        "User Data Directory:".bright_white(),
        gradient_path(&paths.user_data.display().to_string())
    );
    println!("     Purpose: Persistent results and cache data");
    if paths.user_data.exists() {
        println!(
            "     Status: {} (ready for data storage)",
            "[ACTIVE]".green()
        );
    } else {
        println!(
            "     Status: {} (will be created when needed)",
            "[NOT_CREATED]".yellow()
        );
    }
    println!();

    // System templates
    println!(
        "   {} {}",
        "System Templates:".bright_white(),
        gradient_path(&paths.system_templates.display().to_string())
    );
    println!("     Purpose: System-wide default configurations");
    if paths.system_templates.exists() {
        if let Ok(entries) = std::fs::read_dir(&paths.system_templates) {
            let count = entries
                .filter(|e| {
                    if let Ok(entry) = e {
                        entry
                            .path()
                            .extension()
                            .map_or(false, |ext| ext == "yaml" || ext == "yml")
                    } else {
                        false
                    }
                })
                .count();
            println!(
                "     Status: {} ({} templates available)",
                "[ACTIVE]".green(),
                count
            );
        } else {
            println!(
                "     Status: {} (directory exists but unreadable)",
                "[WARNING]".yellow()
            );
        }
    } else {
        println!(
            "     Status: {} (using development fallback)",
            "[DEVELOPMENT]".cyan()
        );
    }
    println!();

    // Output Directories
    println!("{}", "[OUTPUT] Output Directories:".bright_magenta());

    // Show current/default output directory
    let output_base = args
        .output
        .as_ref()
        .map(|p| p.clone())
        .unwrap_or_else(|| paths.default_output_dir());

    let is_custom = args.output.is_some();
    let output_type = if is_custom {
        "Custom Output Directory"
    } else if paths.development_output_dir() == output_base {
        "Default Output Directory (Development Mode)"
    } else {
        "Default Output Directory (Production Mode)"
    };

    println!(
        "   {} {}",
        output_type.bright_white(),
        gradient_path(&output_base.display().to_string())
    );
    println!("     Purpose: Scan results and execution logs");
    if output_base.exists() {
        if let Ok(entries) = std::fs::read_dir(&output_base) {
            let count = entries.count();
            println!(
                "     Status: {} ({} scan results)",
                "[ACTIVE]".green(),
                count
            );
        } else {
            println!(
                "     Status: {} (directory exists but unreadable)",
                "[WARNING]".yellow()
            );
        }
    } else {
        println!(
            "     Status: {} (will be created on first scan)",
            "[NOT_CREATED]".yellow()
        );
    }
    println!();

    // Show development vs production paths if not using custom output
    if !is_custom {
        println!(
            "   {} {}",
            "Development Output:".bright_white(),
            gradient_path(&paths.development_output_dir().display().to_string())
        );
        println!("     Purpose: Local project development and testing");
        println!();

        println!(
            "   {} {}",
            "Production Output:".bright_white(),
            gradient_path(&paths.production_output_dir().display().to_string())
        );
        println!("     Purpose: System-wide installation results");
        println!();

        println!(
            "   {} The tool automatically selects based on execution context",
            "[INFO]".bright_blue()
        );
        println!("     Use -o/--output to specify a custom location");
    }
    println!();

    // Available Configurations
    println!("{}", "[CONFIGS] Available Configurations:".bright_cyan());
    let configs = paths.list_available_configs();
    if configs.is_empty() {
        println!("   {} No configurations found", "[WARNING]".yellow());
    } else {
        for (name, path) in configs {
            println!(
                "   - {} -> {}",
                name.bright_white(),
                gradient_path(&path.display().to_string())
            );
        }
    }
    println!();

    // Usage Examples
    println!("{}", "[EXAMPLES] Usage Examples:".bright_green());
    println!("   # Use with profile name:");
    println!(
        "   {} --target example.com --config default",
        "ipcrawler".bright_cyan()
    );
    println!("   ");
    println!("   # Create user config directory:");
    println!(
        "   {} -p {}",
        "mkdir".bright_cyan(),
        paths.user_config.join("profiles").display()
    );
    println!("   ");
    println!("   # Copy system template to user directory:");
    println!(
        "   {} {} {}",
        "cp".bright_cyan(),
        paths.system_templates.join("default.yaml").display(),
        paths
            .user_config
            .join("profiles")
            .join("my-custom.yaml")
            .display()
    );
    println!();

    println!(
        "{}",
        "[INFO] For more details, use: ipcrawler --config nonexistent --validate".bright_black()
    );
}

fn print_tools_info(config: &Config) {
    println!("{}", "[TOOLS] Available Tools".bright_cyan().bold());
    println!();

    println!("{}", "[CONFIG] Configured Tools:".bright_blue());
    if config.tools.is_empty() {
        println!("   {} No tools configured", "[WARNING]".yellow());
        return;
    }

    for (i, tool) in config.tools.iter().enumerate() {
        let status = if tool.enabled {
            "[ENABLED]"
        } else {
            "[DISABLED]"
        };
        let status_color = if tool.enabled {
            status.green()
        } else {
            status.red()
        };

        println!(
            "   {}. {} - {}",
            (i + 1).to_string().bright_white(),
            tool.name.bright_white(),
            status_color
        );
        println!("      Command: {}", tool.command.bright_black());
        println!(
            "      Timeout: {}s | Output: {}",
            tool.timeout,
            tool.output_file.bright_black()
        );
        println!();
    }

    if !config.chains.is_empty() {
        println!("{}", "[CHAINS] Tool Chains:".bright_magenta());
        for chain in &config.chains {
            println!(
                "   {} -> {} ({})",
                chain.from.bright_cyan(),
                chain.to.bright_cyan(),
                chain.condition.bright_black()
            );
        }
        println!();
    }

    println!("{}", "[SETTINGS] Global Settings:".bright_yellow());
    println!(
        "   Max Concurrent: {}",
        config.globals.max_concurrent.to_string().bright_white()
    );
    println!(
        "   Retry Count: {}",
        config.globals.retry_count.to_string().bright_white()
    );
    println!("   Log Level: {}", config.globals.log_level.bright_white());
}

fn print_dry_run_info(
    config: &Config,
    target: &str,
    output_dir: &PathBuf,
    progress: &ProgressManager,
) {
    progress.print_section("Execution Plan");

    progress.print_subsection("Target:", target);
    progress.print_subsection("Output:", &output_dir.display().to_string());

    let enabled_tools: Vec<_> = config.tools.iter().filter(|t| t.enabled).collect();

    if enabled_tools.is_empty() {
        progress.print_warning("No enabled tools to execute");
        return;
    }

    progress.print_section(&format!(
        "Tools to Execute ({} tools):",
        enabled_tools.len()
    ));

    for (i, tool) in enabled_tools.iter().enumerate() {
        let mut command = tool.command.clone();
        command = command.replace("{target}", target);
        command = command.replace("{output}", &output_dir.to_string_lossy());

        progress.print_subsection(&format!("{}. {}", i + 1, tool.name), "");
        progress.print_subsection("  Command:", &command);
        progress.print_subsection("  Timeout:", &format!("{}s", tool.timeout));
    }

    if !config.chains.is_empty() {
        progress.print_section("Execution Order (with chaining):");

        // Simple dependency resolution for display
        let mut remaining_tools: Vec<_> = enabled_tools.iter().map(|t| t.name.as_str()).collect();
        let mut execution_order = Vec::new();
        let mut round = 1;

        while !remaining_tools.is_empty() && round <= 10 {
            // Prevent infinite loop
            let mut ready_tools = Vec::new();

            for tool_name in &remaining_tools {
                let has_unmet_deps = config.chains.iter().any(|chain| {
                    chain.to == *tool_name && !execution_order.contains(&chain.from.as_str())
                });

                if !has_unmet_deps {
                    ready_tools.push(*tool_name);
                }
            }

            if ready_tools.is_empty() {
                // Circular dependency or other issue
                execution_order.extend(remaining_tools.iter());
                break;
            }

            progress.print_subsection(&format!("Round {}:", round), &ready_tools.join(", "));
            execution_order.extend(ready_tools.iter());
            remaining_tools.retain(|t| !ready_tools.contains(t));
            round += 1;
        }
        println!();
    }

    progress.print_section("Execution Settings:");
    progress.print_subsection(
        "Max Concurrent:",
        &config.globals.max_concurrent.to_string(),
    );
    progress.print_subsection("Retry Count:", &config.globals.retry_count.to_string());

    progress.print_info("Use without --dry-run to execute this plan");
}

async fn handle_list_configs(paths: &ReconPaths) -> Result<(), Box<dyn std::error::Error>> {
    use std::collections::HashMap;

    println!(
        "{}",
        "[CONFIGS] Available Configuration Profiles"
            .bright_cyan()
            .bold()
    );
    println!();

    // Collect all configs with their metadata
    let mut config_groups: HashMap<String, Vec<(String, PathBuf, Option<Config>)>> = HashMap::new();

    // Scan all directories for YAML files
    let directories = vec![
        ("Production Templates", paths.system_templates.clone()),
        ("User Profiles", paths.user_config.join("profiles")),
        ("Testing Configs", paths.working_dir.join("testing")),
    ];

    for (group_name, dir_path) in directories {
        if dir_path.exists() {
            if let Ok(entries) = std::fs::read_dir(&dir_path) {
                let mut configs = Vec::new();

                for entry in entries.flatten() {
                    let path = entry.path();
                    if path
                        .extension()
                        .map_or(false, |ext| ext == "yaml" || ext == "yml")
                    {
                        if let Some(name) = path.file_stem().and_then(|s| s.to_str()) {
                            // Try to load config to get metadata
                            let config = Config::from_file(&path).ok();
                            configs.push((name.to_string(), path, config));
                        }
                    }
                }

                if !configs.is_empty() {
                    configs.sort_by(|a, b| a.0.cmp(&b.0));
                    config_groups.insert(group_name.to_string(), configs);
                }
            }
        }
    }

    // Display in tree format
    let group_order = ["Production Templates", "User Profiles", "Testing Configs"];

    for (group_index, group_name) in group_order.iter().enumerate() {
        if let Some(configs) = config_groups.get(*group_name) {
            // Group header with tree characters
            let group_connector = if group_index == group_order.len() - 1
                && !group_order
                    .iter()
                    .skip(group_index + 1)
                    .any(|g| config_groups.contains_key(*g))
            {
                "└──"
            } else {
                "├──"
            };

            println!(
                "{} {} {}",
                group_connector.bright_blue(),
                "[DIR]".bright_yellow(),
                group_name.bright_white().bold()
            );

            // List configs in this group
            for (config_index, (name, path, config_opt)) in configs.iter().enumerate() {
                let is_last_config = config_index == configs.len() - 1;
                let is_last_group = group_index == group_order.len() - 1
                    || !group_order
                        .iter()
                        .skip(group_index + 1)
                        .any(|g| config_groups.contains_key(*g));

                let prefix = if is_last_group && is_last_config {
                    "    └──"
                } else if is_last_config {
                    "│   └──"
                } else if is_last_group {
                    "    ├──"
                } else {
                    "│   ├──"
                };

                // Config name
                print!(
                    "{} {} {}",
                    prefix.bright_blue(),
                    "[CFG]".bright_green(),
                    name.bright_cyan().bold()
                );

                // Add description if available
                if let Some(config) = config_opt {
                    if !config.metadata.description.is_empty() {
                        print!(
                            " {}",
                            format!("- {}", config.metadata.description).bright_black()
                        );
                    }
                    if !config.metadata.version.is_empty() {
                        print!(
                            " {}",
                            format!("(v{})", config.metadata.version).bright_purple()
                        );
                    }
                }
                println!();

                // Show file path as sub-item
                let path_prefix = if is_last_group && is_last_config {
                    "        └──"
                } else if is_last_config {
                    "│       └──"
                } else if is_last_group {
                    "    │   └──"
                } else {
                    "│   │   └──"
                };

                println!(
                    "{} {} {}",
                    path_prefix.bright_black(),
                    "[FILE]".bright_black(),
                    gradient_path(&path.display().to_string())
                );

                // Show tool count if config loaded successfully
                if let Some(config) = config_opt {
                    let enabled_tools = config.tools.iter().filter(|t| t.enabled).count();
                    let total_tools = config.tools.len();
                    let has_chains = !config.chains.is_empty();

                    let info_prefix = if is_last_group && is_last_config {
                        "        "
                    } else if is_last_config {
                        "│       "
                    } else if is_last_group {
                        "    │   "
                    } else {
                        "│   │   "
                    };

                    print!(
                        "{} {} {} tools enabled",
                        info_prefix.bright_black(),
                        "[TOOLS]".bright_black(),
                        enabled_tools.to_string().bright_white()
                    );

                    if total_tools != enabled_tools {
                        print!(" ({} total)", total_tools.to_string().bright_black());
                    }

                    if has_chains {
                        print!(" | {}", "[CHAINED]".bright_black());
                    }

                    println!();
                }

                // Add spacing between configs
                if !is_last_config {
                    println!();
                }
            }

            // Add spacing between groups
            if group_index < group_order.len() - 1 {
                println!();
            }
        }
    }

    // Summary footer
    let total_configs: usize = config_groups.values().map(|v| v.len()).sum();
    println!();
    println!(
        "{} {} Found {} configuration profiles across {} locations",
        "[SUMMARY]".bright_blue(),
        "Summary:".bright_white().bold(),
        total_configs.to_string().bright_cyan(),
        config_groups.len().to_string().bright_cyan()
    );

    // Usage examples
    println!();
    println!(
        "{} {} Usage examples:",
        "[TIPS]".bright_yellow(),
        "Tips:".bright_white().bold()
    );

    if let Some(first_group) = config_groups.values().next() {
        if let Some((first_config, _, _)) = first_group.first() {
            println!(
                "   {} Run a scan: {}",
                "-".bright_blue(),
                format!("ipcrawler -t target.com -c {}", first_config).bright_cyan()
            );
        }
    }

    println!(
        "   {} Multiple configs: {}",
        "-".bright_blue(),
        "ipcrawler -t target.com -c quick-scan,web-scan".bright_cyan()
    );

    println!(
        "   {} View tools in config: {}",
        "-".bright_blue(),
        "ipcrawler -c config-name --list-tools".bright_cyan()
    );

    Ok(())
}

async fn handle_update() -> Result<(), Box<dyn std::error::Error>> {
    use std::process::Command;

    println!("{}", "[UPDATE] ipcrawler Update".bright_cyan().bold());
    println!();

    // Check current version
    let current_version = env!("CARGO_PKG_VERSION");
    println!(
        "{} Current version: {}",
        "[VERSION]".bright_blue(),
        current_version.bright_white()
    );

    // Check if running from installed location or development
    let exe_path = std::env::current_exe()?;
    let is_cargo_installed = exe_path.to_string_lossy().contains(".cargo/bin");
    let is_system_installed = exe_path.to_string_lossy().contains("/usr/local/bin")
        || exe_path.to_string_lossy().contains("/usr/bin");

    if is_cargo_installed {
        // Update via cargo
        println!(
            "{} Updating via cargo install...",
            "[UPDATING]".bright_yellow()
        );

        let output = Command::new("cargo")
            .args(&["install", "--force", "ipcrawler"])
            .output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    println!(
                        "{} ipcrawler updated successfully!",
                        "[SUCCESS]".bright_green()
                    );
                    println!();
                    println!(
                        "{} Run 'ipcrawler --version' to verify the update",
                        "[INFO]".bright_blue()
                    );
                } else {
                    // Try from git if crates.io fails
                    println!(
                        "{} Cargo install failed, trying from source...",
                        "[WARNING]".bright_yellow()
                    );

                    let git_output = Command::new("cargo")
                        .args(&[
                            "install",
                            "--force",
                            "--git",
                            "https://github.com/your-username/ipcrawler-rust.git",
                        ])
                        .output();

                    match git_output {
                        Ok(git_result) if git_result.status.success() => {
                            println!(
                                "{} ipcrawler updated successfully from source!",
                                "[SUCCESS]".bright_green()
                            );
                        }
                        _ => {
                            println!("{} Failed to update from source", "[ERROR]".bright_red());
                            println!("{} Please update manually:", "[INFO]".bright_blue());
                            println!(
                                "    cargo install --force --git https://github.com/your-username/ipcrawler-rust.git"
                            );
                        }
                    }
                }
            }
            Err(e) => {
                println!("{} Failed to run cargo: {}", "[ERROR]".bright_red(), e);
                println!(
                    "{} Please ensure cargo is in your PATH",
                    "[INFO]".bright_blue()
                );
            }
        }
    } else if is_system_installed {
        // Update via install script
        println!(
            "{} System installation detected",
            "[DETECTED]".bright_blue()
        );
        println!("{} Running update script...", "[UPDATING]".bright_yellow());

        let temp_script = "/tmp/ipcrawler-update.sh";

        // Download and run update script
        let download_cmd = format!(
            "curl -sSL https://install.ipcrawler.io/update.sh -o {} && chmod +x {} && {}",
            temp_script, temp_script, temp_script
        );

        let output = Command::new("sh").arg("-c").arg(&download_cmd).output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    println!(
                        "{} ipcrawler updated successfully!",
                        "[SUCCESS]".bright_green()
                    );
                } else {
                    println!("{} Update script failed", "[ERROR]".bright_red());
                    println!(
                        "{} You can manually update by running:",
                        "[INFO]".bright_blue()
                    );
                    println!("    curl -sSL https://install.ipcrawler.io | bash");
                }
            }
            Err(e) => {
                println!(
                    "{} Failed to download update script: {}",
                    "[ERROR]".bright_red(),
                    e
                );
                println!(
                    "{} Please run the installer manually:",
                    "[INFO]".bright_blue()
                );
                println!("    curl -sSL https://install.ipcrawler.io | bash");
            }
        }

        // Clean up
        let _ = Command::new("rm").arg("-f").arg(temp_script).output();
    } else {
        // Development version or unknown installation
        println!(
            "{} Development version detected",
            "[DETECTED]".bright_blue()
        );
        println!(
            "{} To update, pull latest changes and rebuild:",
            "[INFO]".bright_blue()
        );
        println!("    git pull");
        println!("    cargo build --release");
        println!();
        println!("{} Or install system-wide:", "[INFO]".bright_blue());
        println!("    cargo install --path .");
    }

    Ok(())
}

async fn handle_resume_scan(
    resume_dir: &PathBuf,
    _paths: &ReconPaths,
    _args: &cli::Cli,
) -> Result<(), Box<dyn std::error::Error>> {
    println!("{}", "[RESUME] Scan Resumption".bright_cyan().bold());
    println!();

    if !resume_dir.exists() {
        println!(
            "{} Resume directory does not exist: {}",
            "[ERROR]".bright_red(),
            resume_dir.display()
        );
        return Ok(());
    }

    // Check for existing scan data
    let json_report = resume_dir.join("scan_summary.json");
    let logs_dir = resume_dir.join("logs");
    let raw_dir = resume_dir.join("raw");

    if json_report.exists() {
        println!(
            "{} Found existing scan report: {}",
            "[FOUND]".bright_green(),
            json_report.display()
        );

        // Try to parse existing results
        if let Ok(content) = fs::read_to_string(&json_report) {
            if let Ok(summary) = serde_json::from_str::<output::ScanSummary>(&content) {
                println!("{} Previous scan:", "[SCAN]".bright_blue());
                println!("   Target: {}", summary.metadata.target.bright_white());
                println!("   Duration: {:.2}s", summary.metadata.duration_seconds);
                println!(
                    "   Tools: {} successful, {} failed",
                    summary.execution_stats.successful_tools.to_string().green(),
                    summary.execution_stats.failed_tools.to_string().red()
                );
                let ports_count = summary
                    .discoveries
                    .iter()
                    .filter(|d| matches!(d.discovery_type, output::DiscoveryType::Port { .. }))
                    .count();
                println!(
                    "   Ports found: {}",
                    ports_count.to_string().bright_yellow()
                );
                println!();
            }
        }
    }

    if logs_dir.exists() {
        println!(
            "{} Found logs directory: {}",
            "[LOGS]".bright_blue(),
            logs_dir.display()
        );
    }

    if raw_dir.exists() {
        if let Ok(entries) = fs::read_dir(&raw_dir) {
            let file_count = entries.count();
            println!(
                "{} Found {} raw output files in: {}",
                "[FILES]".bright_yellow(),
                file_count,
                raw_dir.display()
            );
        }
    }

    println!();
    println!(
        "{} Scan resumption is not yet fully implemented",
        "[WIP]".bright_yellow()
    );
    println!(
        "{} This feature will allow continuing interrupted scans",
        "[INFO]".bright_blue()
    );
    println!(
        "{} For now, you can review the existing results above",
        "[INFO]".bright_blue()
    );

    Ok(())
}
