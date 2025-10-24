mod cli;
mod config;
mod executor;
mod llm;
mod output;
mod system;
mod tools;
mod ui;

use anyhow::Result;
use chrono::Local;
use clap::Parser;
use cli::{parse_ports, parse_targets, Cli};
use config::WordlistConfig;
use executor::queue::{Task, TaskQueue};
use executor::runner::TaskRunner;
use llm::{LLMClient, LLMConfig, LLMProvider, PromptTemplate, SecurityAnalysisPrompt};
use output::parser::OutputParser;
use output::reporter::ReportGenerator;
use std::fs;
use std::path::PathBuf;
use std::time::Duration;
use system::detect::is_running_as_root;
use tokio::sync::mpsc;
use tools::{ToolChecker, ToolRegistry};
use ui::TerminalUI;

#[tokio::main]
async fn main() -> Result<()> {
    // Load environment variables from .env file if it exists
    if let Err(e) = dotenvy::dotenv() {
        if !e.not_found() {
            eprintln!("Warning: Failed to load .env file: {}", e);
        }
    }

    let cli = Cli::parse();

    // Detect sudo/root privileges at startup
    let running_as_root = is_running_as_root();
    if running_as_root {
        println!("Running with elevated privileges (sudo/root)");
    } else {
        println!("Running without elevated privileges");
        println!("Note: Some tools may require sudo for optimal results");
    }

    // Load wordlist configuration
    let wordlist_config = WordlistConfig::load_default().unwrap_or_else(|e| {
        eprintln!("Warning: Failed to load wordlist config: {}", e);
        eprintln!("Using default wordlist path");
        WordlistConfig {
            wordlists: std::collections::HashMap::new(),
        }
    });

    let wordlist_path = wordlist_config.resolve(&cli.wordlist).unwrap_or_else(|_| {
        eprintln!(
            "Warning: Wordlist '{}' not found, using as direct path",
            cli.wordlist
        );
        cli.wordlist.clone()
    });

    println!("Using wordlist: {}", wordlist_path);

    // Create LLM client if enabled
    let llm_client = if cli.use_llm {
        let provider_str = cli.llm_provider.as_str();
        let provider = match provider_str {
            "openai" => LLMProvider::OpenAI,
            "claude" => LLMProvider::Claude,
            "ollama" => LLMProvider::Ollama,
            _ => anyhow::bail!("Unsupported LLM provider: {}", cli.llm_provider),
        };

        // Get API key from CLI argument, then provider-specific env var, then generic LLM_API_KEY
        let api_key = cli
            .llm_api_key
            .or_else(|| std::env::var("OPENAI_API_KEY").ok())
            .or_else(|| std::env::var("ANTHROPIC_API_KEY").ok())
            .or_else(|| std::env::var("LLM_API_KEY").ok());

        if matches!(provider, LLMProvider::OpenAI | LLMProvider::Claude) && api_key.is_none() {
            anyhow::bail!(
                "API key required for {}. Set --llm-api-key or configure in .env file:\n  - For OpenAI: OPENAI_API_KEY=your_key\n  - For Claude: ANTHROPIC_API_KEY=your_key", 
                cli.llm_provider
            );
        }

        // Get model from CLI, then provider-specific env var, then default
        let model = if !cli.llm_model.is_empty() {
            cli.llm_model.clone()
        } else {
            match provider {
                LLMProvider::OpenAI => {
                    std::env::var("OPENAI_MODEL").unwrap_or_else(|_| "gpt-4".to_string())
                }
                LLMProvider::Claude => std::env::var("CLAUDE_MODEL")
                    .unwrap_or_else(|_| "claude-3-sonnet-20240229".to_string()),
                LLMProvider::Ollama => {
                    std::env::var("OLLAMA_MODEL").unwrap_or_else(|_| "llama3.1".to_string())
                }
            }
        };

        // Get base URL from CLI, then provider-specific env var, then default
        let base_url = cli.llm_base_url.clone().or_else(|| match provider {
            LLMProvider::OpenAI => std::env::var("OPENAI_BASE_URL").ok(),
            LLMProvider::Claude => std::env::var("CLAUDE_BASE_URL").ok(),
            LLMProvider::Ollama => std::env::var("OLLAMA_BASE_URL").ok(),
        });

        let config = LLMConfig {
            provider,
            api_key,
            model,
            base_url,
            timeout: Duration::from_secs(30),
        };

        let client = LLMClient::new(config);

        // Test LLM connection if enabled
        if let Err(e) = client.test_connection().await {
            eprintln!("Warning: LLM connection test failed: {}", e);
            eprintln!("Continuing without LLM analysis...");
            None
        } else {
            println!("✓ LLM connection established");

            // Test template functionality
            let template = PromptTemplate::new(
                "Analyze security tool output".to_string(),
                "Tool: {tool_name}\nOutput: {output}\n\nProvide security analysis.".to_string(),
            );

            if client
                .analyze_with_template(&template, "test", "sample output")
                .await
                .is_ok()
            {
                println!("✓ LLM template analysis working");
            }

            // Test build_security_prompt method
            let test_prompt = client.build_security_prompt("nmap", "22/tcp open ssh");
            println!("✓ Security prompt generated: {} chars", test_prompt.len());

            // Test SecurityAnalysisPrompt
            let system_prompt = SecurityAnalysisPrompt::system_prompt();
            println!("✓ System prompt available: {} chars", system_prompt.len());

            // Test get_system_prompt method
            let template_system_prompt = client.get_security_system_prompt();
            println!(
                "✓ Template system prompt: {} chars",
                template_system_prompt.len()
            );

            Some(client)
        }
    } else {
        None
    };

    let targets = parse_targets(&cli.target)?;
    let ports = parse_ports(&cli.ports)?;

    let output_dir = cli.output.unwrap_or_else(|| {
        let time_str = Local::now().format("%H%M");
        let target_str = if targets.len() == 1 {
            targets[0].clone()
        } else {
            "multiple".to_string()
        };
        PathBuf::from(format!("./ipcrawler-results/{}_{}", target_str, time_str))
    });

    fs::create_dir_all(&output_dir)?;

    println!("Loading tools from: {}", cli.tools_dir.display());
    let mut registry = ToolRegistry::new(&cli.tools_dir);
    let tool_count = registry.discover_tools()?;

    if tool_count == 0 {
        eprintln!(
            "No tools found in {}. Please add YAML tool definitions.",
            cli.tools_dir.display()
        );
        std::process::exit(1);
    }

    println!("Loaded {} tools", tool_count);

    // Perform comprehensive tool availability check
    let checker = ToolChecker::new();
    let all_tools: Vec<&_> = registry.get_all_tools();
    let availability_report = checker.check_all_tools(&all_tools);

    println!("\nChecking tool availability...");
    println!("{}", checker.get_installation_summary(&availability_report));

    if availability_report.missing_count > 0 {
        let install_all = checker.prompt_install_all(&availability_report)?;

        if install_all {
            checker.install_missing_tools(&availability_report)?;
        } else {
            checker.prompt_individual_installs(&availability_report)?;
        }

        // Re-check tool availability after installation
        println!("\nVerifying installed tools...");
        let all_tools: Vec<&_> = registry.get_all_tools();
        let verification_report = checker.check_all_tools(&all_tools);

        if verification_report.missing_count > 0 {
            eprintln!(
                "\nWARNING: {} tools are still missing after installation:",
                verification_report.missing_count
            );
            for status in &verification_report.tools {
                if !status.installed {
                    eprintln!("  ✗ {} (binary: {})", status.name, status.binary);
                }
            }
            eprintln!("\nThe scan will proceed but these tools will be skipped.");
        } else {
            println!("✓ All tools are now installed and available!");
        }
    }

    println!("\nGenerating tasks...");
    let mut queue = TaskQueue::new();

    // Get final tool availability status
    let all_tools: Vec<&_> = registry.get_all_tools();
    let final_check = checker.check_all_tools(&all_tools);

    // Create a hashset of installed tool names for quick lookup
    let installed_tools: std::collections::HashSet<String> = final_check
        .tools
        .iter()
        .filter(|status| status.installed)
        .map(|status| status.name.clone())
        .collect();

    for tool in registry.get_all_tools() {
        // Skip tools that are not installed
        if !installed_tools.contains(&tool.name) {
            continue;
        }

        for target in &targets {
            // Check if tool needs all ports at once (batch scanning like nmap)
            let needs_ports_batch = tool.command.contains("{{ports}}")
                || tool
                    .sudo_command
                    .as_ref()
                    .is_some_and(|c| c.contains("{{ports}}"));

            // Check if tool needs individual port scanning
            let needs_port_individual = tool.command.contains("{{port}}")
                || tool
                    .sudo_command
                    .as_ref()
                    .is_some_and(|c| c.contains("{{port}}"));

            if needs_ports_batch {
                // Create ONE task that scans all ports (efficient for nmap, masscan, etc.)
                match Task::new_with_ports(
                    tool,
                    target.clone(),
                    &ports,
                    &output_dir,
                    running_as_root,
                    Some(&wordlist_path),
                ) {
                    Ok(task) => queue.add_task(task),
                    Err(e) => eprintln!("Failed to create task: {}", e),
                }
            } else if needs_port_individual {
                // Create one task per port (for port-specific tools like nikto, whatweb)
                for port in &ports {
                    match Task::new(
                        tool,
                        target.clone(),
                        Some(*port),
                        &output_dir,
                        running_as_root,
                        Some(&wordlist_path),
                    ) {
                        Ok(task) => queue.add_task(task),
                        Err(e) => eprintln!("Failed to create task: {}", e),
                    }
                }
            } else {
                // Tool doesn't need ports (like whois, ping, traceroute)
                match Task::new(
                    tool,
                    target.clone(),
                    None,
                    &output_dir,
                    running_as_root,
                    Some(&wordlist_path),
                ) {
                    Ok(task) => queue.add_task(task),
                    Err(e) => eprintln!("Failed to create task: {}", e),
                }
            }
        }
    }

    let total_tasks = queue.len();
    println!("Created {} tasks", total_tasks);

    if total_tasks == 0 {
        eprintln!("No tasks to execute. Exiting.");
        std::process::exit(1);
    }

    let results = if cli.dry_run {
        println!("DRY RUN MODE: Not executing tools, showing what would be parsed...");

        // Create sample results for testing parse_sync method
        let mut sample_results = Vec::new();
        for tool in registry.get_all_tools().into_iter().take(3) {
            // Limit to 3 tools for demo
            if installed_tools.contains(&tool.name) {
                let sample_result = crate::executor::runner::TaskResult {
                    task_id: crate::executor::queue::TaskId::new(&tool.name, "192.168.1.1", None),
                    tool_name: tool.name.clone(),
                    target: "192.168.1.1".to_string(),
                    port: None,
                    actual_command: tool.command.clone(),
                    status: crate::executor::queue::TaskStatus::Completed {
                        duration: std::time::Duration::from_millis(100),
                        exit_code: 0,
                    },
                    stdout: format!("Sample output from {}", tool.name),
                    stderr: String::new(),
                };

                // Test parse_sync method
                match OutputParser::parse_sync(tool, &sample_result) {
                    Ok(findings) => {
                        println!("✓ {} would generate {} findings", tool.name, findings.len());
                    }
                    Err(e) => {
                        println!("✗ Error parsing {}: {}", tool.name, e);
                    }
                }

                sample_results.push(sample_result);
            }
        }
        sample_results
    } else {
        let runner = TaskRunner::new(10);

        let (update_tx, update_rx) = mpsc::unbounded_channel();

        let mut ui = TerminalUI::new(targets.clone(), ports.clone());

        let tasks: Vec<Task> = {
            let mut task_list = Vec::new();
            while let Some(task) = queue.pop() {
                task_list.push(task);
            }
            task_list
        };

        let ui_handle = tokio::spawn(async move { ui.run(update_rx).await });

        let results = runner.run_tasks(tasks.clone(), update_tx).await;

        let _ = ui_handle.await;
        results
    };

    println!("\nProcessing results...");

    let mut all_findings = Vec::new();

    for result in &results {
        if let Some(tool) = registry.get_tool(&result.tool_name) {
            // Use different parsing methods based on verbose mode
            let findings = if cli.verbose {
                // Use the original parse method in verbose mode
                match OutputParser::parse(tool, result, cli.use_llm).await {
                    Ok(f) => {
                        println!(
                            "✓ Parsed {} output with {} findings",
                            result.tool_name,
                            f.len()
                        );
                        f
                    }
                    Err(e) => {
                        eprintln!("Error parsing output for {}: {}", result.tool_name, e);
                        Vec::new()
                    }
                }
            } else {
                // Use the enhanced parse_with_llm method in normal mode
                match OutputParser::parse_with_llm(tool, result, llm_client.as_ref()).await {
                    Ok(f) => f,
                    Err(e) => {
                        eprintln!("Error parsing output for {}: {}", result.tool_name, e);
                        Vec::new()
                    }
                }
            };

            all_findings.extend(findings);
        }
    }

    all_findings = OutputParser::deduplicate(all_findings);
    OutputParser::sort_by_severity(&mut all_findings);

    println!("Found {} findings", all_findings.len());

    println!("\nGenerating reports...");

    ReportGenerator::generate_markdown(&all_findings, &results, &targets, &ports, &output_dir)?;

    ReportGenerator::save_json(&all_findings, &results, &output_dir)?;

    ReportGenerator::save_individual_logs(&results, &output_dir)?;

    println!("\nScan complete!");
    println!("Reports saved to: {}", output_dir.display());
    println!("  - report.md: Markdown summary report");
    println!("  - results.json: JSON results");
    println!("  - logs/: Individual tool outputs");

    Ok(())
}
