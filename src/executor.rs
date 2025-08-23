use crate::config::{Config, Tool};
use crate::progress::ProgressManager;
use crate::error_handler::{ErrorHandler, ErrorContext, EmergencyStopError};
use crate::gradient::{gradient_ports, gradient_tool};
use chrono::Local;
use indicatif::ProgressBar;
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::Write;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;
use tokio::fs::OpenOptions;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader as AsyncBufReader};
use tokio::process::Command;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::timeout;
use tokio::signal;
use tokio::task::JoinHandle;

#[derive(Clone)]
pub struct ToolResult {
    pub tool_name: String,
    pub exit_code: i32,
    #[allow(dead_code)]
    pub stdout_file: PathBuf,
    #[allow(dead_code)]
    pub stderr_file: PathBuf,
    pub duration: Duration,
    #[allow(dead_code)]
    pub has_output: bool,
    pub error: Option<String>,
}

pub struct ExecutionContext {
    pub output_dir: PathBuf,
    pub target: String,
    pub debug: bool,
    pub verbose: bool,
}

pub struct Executor {
    config: Config,
    context: ExecutionContext,
    results: Arc<Mutex<HashMap<String, ToolResult>>>,
    progress_manager: Arc<ProgressManager>,
    log_file: Arc<Mutex<File>>,
    error_handler: ErrorHandler,
}

impl Executor {
    pub fn new(config: Config, context: ExecutionContext, progress_manager: Arc<ProgressManager>, emergency_stop: bool, notifications: bool) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let log_path = context.output_dir.join("logs").join("execution.log");
        let log_file = File::options()
            .create(true)
            .append(true)
            .open(&log_path)?;
        
        // Initialize error handler with user-specified settings
        let error_handler = ErrorHandler::new(
            progress_manager.clone(),
            &context.output_dir,
            emergency_stop,
            notifications,
        )?;
        
        Ok(Self {
            config,
            context,
            results: Arc::new(Mutex::new(HashMap::new())),
            progress_manager,
            log_file: Arc::new(Mutex::new(log_file)),
            error_handler,
        })
    }

    pub async fn execute_all(&mut self) -> Result<Vec<ToolResult>, Box<dyn std::error::Error + Send + Sync>> {
        // Create discovery tracking for standalone execution
        let discovery_bar = self.progress_manager.create_discovery_bar();
        
        let results = self.execute_batch(&discovery_bar).await?;
        
        // Finish discovery tracking
        discovery_bar.finish();
        
        Ok(results)
    }

    pub async fn execute_batch(&mut self, _discovery_bar: &ProgressBar) -> Result<Vec<ToolResult>, Box<dyn std::error::Error + Send + Sync>> {
        self.log_info("Starting tool execution").await?;
        
        let enabled_tools: Vec<Tool> = self.config.tools.clone()
            .into_iter()
            .filter(|t| t.enabled)
            .collect();
        
        if enabled_tools.is_empty() {
            self.log_warning("No enabled tools to execute").await?;
            return Ok(Vec::new());
        }
        
        // Show initial queue status in verbose mode
        if enabled_tools.len() > 1 {
            let queue_names: Vec<String> = enabled_tools.iter().map(|t| t.name.clone()).collect();
            self.progress_manager.print_verbose_info(&format!("Queue: {}", queue_names.join(", ")), self.context.verbose);
        }
        
        // Set up Ctrl+C handler
        let shutdown = Arc::new(Mutex::new(false));
        let shutdown_clone = shutdown.clone();
        
        tokio::spawn(async move {
            signal::ctrl_c().await.expect("Failed to listen for Ctrl+C");
            let mut shutdown_guard = shutdown_clone.lock().await;
            *shutdown_guard = true;
            // Shutdown handled gracefully via MultiProgress
        });
        
        // Dynamic concurrency management - spawn tasks as slots become available
        let semaphore = Arc::new(Semaphore::new(self.config.globals.max_concurrent));
        let mut pending_tools = enabled_tools;
        let mut active_tasks = Vec::new();
        let mut completed_results = Vec::new();
        
        // Concurrency info logged to file instead of console output
        
        // Initial spawn up to max_concurrent
        while !pending_tools.is_empty() && active_tasks.len() < self.config.globals.max_concurrent {
            let tool = pending_tools.remove(0);
            let task = self.spawn_tool_task(tool, semaphore.clone()).await;
            active_tasks.push(task);
        }
        
        // Process completions and spawn new tools as slots free up
        while !active_tasks.is_empty() {
            // Wait for any task to complete
            let (result, _task_index, remaining_tasks) = futures::future::select_all(active_tasks).await;
            active_tasks = remaining_tasks;
            
            // Process the completed task
            match result {
                Ok(Ok(tool_result)) => {
                    let duration = format!("{:.1}s", tool_result.duration.as_secs_f64());
                    
                    // Show queue status if there are pending tools
                    let queue_info = if !pending_tools.is_empty() {
                        let queue_names: Vec<String> = pending_tools.iter().map(|t| t.name.clone()).collect();
                        format!(" | Queue: {}", queue_names.join(", "))
                    } else {
                        String::new()
                    };
                    
                    if tool_result.exit_code == 0 {
                        self.progress_manager.print_verbose_success(&format!("{} {}{}", tool_result.tool_name, duration, queue_info), self.context.verbose);
                    } else {
                        // Always show errors, even in non-verbose mode
                        self.progress_manager.print_error(&format!("{} {}{}", tool_result.tool_name, duration, queue_info));
                        
                        // Handle tool failure with error handler
                        let error_ctx = ErrorContext {
                            tool_name: tool_result.tool_name.clone(),
                            error_message: format!("Tool exited with code {}", tool_result.exit_code),
                            exit_code: Some(tool_result.exit_code),
                            timestamp: chrono::Local::now(),
                            command: "command not available".to_string(), // We'd need to pass this from spawn_tool_task
                            output_file: Some(tool_result.stdout_file.clone()),
                        };
                        
                        // Handle the failure - this will return true if emergency stop triggered
                        let should_stop = self.error_handler.handle_tool_failure(error_ctx).await?;
                        
                        if should_stop {
                            // Emergency stop triggered - cancel all remaining tasks
                            self.progress_manager.print_error("Emergency stop triggered - cancelling all remaining tools");
                            
                            // Cancel remaining tasks
                            for task in active_tasks.iter() {
                                task.abort();
                            }
                            
                            return Err(Box::new(EmergencyStopError {
                                message: "Critical tool failure triggered emergency stop".to_string(),
                                failed_tool: tool_result.tool_name.clone(),
                            }));
                        }
                    }
                    
                    // Tool completed - parse output and update discoveries
                    // Validate file size before reading to prevent memory exhaustion
                    if let Err(_) = crate::validator::MemoryValidator::validate_file_size(&tool_result.stdout_file, 50 * 1024 * 1024) { // 50MB limit
                        self.log_error(&format!("Tool {} output file too large, skipping parsing", tool_result.tool_name)).await?;
                    } else if let Ok(content) = std::fs::read_to_string(&tool_result.stdout_file) {
                        // Validate string safety (no null bytes that could cause parsing issues)
                        if let Err(_) = crate::validator::MemoryValidator::validate_string(&content) {
                            self.log_error(&format!("Tool {} output contains invalid characters, skipping parsing", tool_result.tool_name)).await?;
                        } else {
                            let parser = crate::parser::GenericParser::new();
                            let parse_result = parser.parse_output(&content, &tool_result.tool_name);
                        
                        // Memory safety validation for large discovery collections
                        if let Err(_) = crate::validator::MemoryValidator::validate_collection_size(&parse_result.discoveries, 10000) {
                            self.log_error(&format!("Tool {} produced excessive discoveries, truncating results", tool_result.tool_name)).await?;
                        }
                        
                        // Update discovery counters based on parsed results
                        let mut port_count = 0;
                        let mut service_count = 0;
                        let mut vuln_count = 0;
                        
                        for discovery in &parse_result.discoveries {
                            match &discovery.discovery_type {
                                crate::output::DiscoveryType::Port { .. } => port_count += 1,
                                crate::output::DiscoveryType::Service { .. } => service_count += 1,
                                crate::output::DiscoveryType::Vulnerability { .. } => vuln_count += 1,
                                _ => {}
                            }
                        }
                        
                        // Update progress manager with discoveries
                        if port_count > 0 {
                            // Extract unique port numbers
                            let ports: Vec<u16> = parse_result.discoveries.iter()
                                .filter_map(|d| match &d.discovery_type {
                                    crate::output::DiscoveryType::Port { number, .. } => Some(*number),
                                    _ => None
                                })
                                .collect();
                            self.progress_manager.add_discovered_ports(ports);
                        }
                        
                        if service_count > 0 {
                            // Extract unique service descriptions
                            let services: Vec<String> = parse_result.discoveries.iter()
                                .filter_map(|d| match &d.discovery_type {
                                    crate::output::DiscoveryType::Service { name, port, protocol, version } => {
                                        let service_desc = if let Some(ver) = version {
                                            format!("{} {}/{} ({})", name, port, protocol, ver)
                                        } else {
                                            format!("{} {}/{}", name, port, protocol)
                                        };
                                        Some(service_desc)
                                    },
                                    _ => None
                                })
                                .collect();
                            self.progress_manager.add_discovered_services(services);
                        }
                        
                        if vuln_count > 0 {
                            self.progress_manager.add_discovered_vulns(vuln_count);
                        }
                        }
                    }
                    
                    // Cache the result for potential resume functionality
                    {
                        let mut cache = self.results.lock().await;
                        cache.insert(tool_result.tool_name.clone(), tool_result.clone());
                    }
                    
                    completed_results.push(tool_result);
                }
                Ok(Err(e)) => {
                    self.log_error(&format!("Tool execution failed: {}", e)).await?;
                    
                    // Also handle this as a critical error
                    let error_ctx = ErrorContext {
                        tool_name: "unknown".to_string(),
                        error_message: format!("Tool execution failed: {}", e),
                        exit_code: None,
                        timestamp: chrono::Local::now(),
                        command: "unknown".to_string(),
                        output_file: None,
                    };
                    
                    let should_stop = self.error_handler.handle_tool_failure(error_ctx).await?;
                    
                    if should_stop {
                        for task in active_tasks.iter() {
                            task.abort();
                        }
                        return Err(Box::new(EmergencyStopError {
                            message: "Tool execution failure triggered emergency stop".to_string(),
                            failed_tool: "unknown".to_string(),
                        }));
                    }
                }
                Err(e) => {
                    self.log_error(&format!("Task join error: {}", e)).await?;
                    
                    // Handle join errors as critical
                    let error_ctx = ErrorContext {
                        tool_name: "unknown".to_string(),
                        error_message: format!("Task join error: {}", e),
                        exit_code: None,
                        timestamp: chrono::Local::now(),
                        command: "unknown".to_string(),
                        output_file: None,
                    };
                    
                    let should_stop = self.error_handler.handle_tool_failure(error_ctx).await?;
                    
                    if should_stop {
                        for task in active_tasks.iter() {
                            task.abort();
                        }
                        return Err(Box::new(EmergencyStopError {
                            message: "Task join error triggered emergency stop".to_string(),
                            failed_tool: "unknown".to_string(),
                        }));
                    }
                }
            }
            
            // Spawn next tool if any pending and slot available
            if !pending_tools.is_empty() {
                let tool = pending_tools.remove(0);
                // Tool start/stop handled via progress bars
                let task = self.spawn_tool_task(tool, semaphore.clone()).await;
                active_tasks.push(task);
            }
            
            // Check for shutdown signal
            let shutdown_guard = shutdown.lock().await;
            if *shutdown_guard {
                self.log_warning("Execution interrupted by user").await?;
                break;
            }
        }
        
        // Note: Progress bars are managed by the caller (Pipeline or standalone execution)
        
        self.log_info(&format!("Execution complete. {} tools executed", completed_results.len())).await?;
        Ok(completed_results)
    }

    async fn spawn_tool_task(
        &self,
        tool: Tool,
        semaphore: Arc<Semaphore>,
    ) -> JoinHandle<Result<ToolResult, Box<dyn std::error::Error + Send + Sync>>> {
        let context = self.context.clone();
        let progress_manager = self.progress_manager.clone();
        let log_file = self.log_file.clone();
        let retry_count = self.config.globals.retry_count;
        
        // Silent spawning - let the completion messages speak
        
        tokio::spawn(async move {
            let _permit = semaphore.acquire().await.unwrap();
            Self::execute_tool_with_retry(
                tool,
                context,
                progress_manager,
                log_file,
                retry_count
            ).await
        })
    }

    async fn execute_tool_with_retry(
        tool: Tool,
        context: ExecutionContext,
        progress_manager: Arc<ProgressManager>,
        log_file: Arc<Mutex<File>>,
        max_retries: u32,
    ) -> Result<ToolResult, Box<dyn std::error::Error + Send + Sync>> {
        let mut attempt = 0;
        
        loop {
            attempt += 1;
            
            // Create progress bar as a spinner since we don't know actual progress
            let pb = progress_manager.create_spinner(&format!("{}: initializing", tool.name));
            
            let attempt_msg = if attempt > 1 {
                format!(" (attempt {}/{})", attempt, max_retries + 1)
            } else {
                String::new()
            };
            
            // Extract port information from command if available (for nmap)
            let port_info = if tool.command.contains(" -p ") {
                if let Some(port_part) = tool.command.split(" -p ").nth(1) {
                    if let Some(ports) = port_part.split_whitespace().next() {
                        let colored_ports = gradient_ports(ports);
                        format!(" [{}]", colored_ports)
                    } else {
                        String::new()
                    }
                } else {
                    String::new()
                }
            } else {
                String::new()
            };
            
            pb.set_message(format!("{}: scanning{}{}", gradient_tool(&tool.name), port_info, attempt_msg));
            
            match Self::execute_single_tool(tool.clone(), context.clone(), &pb, log_file.clone(), progress_manager.clone()).await {
                Ok(result) => {
                    pb.finish_with_message(format!("{}: completed", gradient_tool(&tool.name)));
                    return Ok(result);
                }
                Err(e) => {
                    if attempt > max_retries {
                        pb.finish_with_message(format!("{}: failed", tool.name));
                        return Err(e);
                    }
                    
                    pb.finish_with_message(format!("{}: retrying", tool.name));
                    tokio::time::sleep(Duration::from_secs(2)).await;
                }
            }
        }
    }

    async fn execute_single_tool(
        tool: Tool,
        context: ExecutionContext,
        pb: &ProgressBar,
        log_file: Arc<Mutex<File>>,
        progress_manager: Arc<ProgressManager>,
    ) -> Result<ToolResult, Box<dyn std::error::Error + Send + Sync>> {
        let start = std::time::Instant::now();
        
        // Prepare output files
        let stdout_file = context.output_dir.join("raw").join(format!("{}.out", tool.name));
        let stderr_file = context.output_dir.join("errors").join(format!("{}.err", tool.name));
        
        // Log execution start
        Self::write_log(&log_file, &format!("Executing: {}", tool.command)).await?;
        
        // Parse command into parts
        let parts: Vec<String> = shell_words::split(&tool.command)?;
        if parts.is_empty() {
            return Err(format!("Invalid command for tool {}", tool.name).into());
        }
        
        let program = &parts[0];
        let args = &parts[1..];
        
        // Create async command
        let mut cmd = Command::new(program);
        cmd.args(args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true);
        
        // Spawn the process
        let mut child = cmd.spawn()?;
        
        // Get stdout and stderr
        let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
        let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;
        
        // Create output files
        let stdout_writer = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&stdout_file)
            .await?;
        
        let stderr_writer = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&stderr_file)
            .await?;
        
        // Create readers
        let stdout_reader = AsyncBufReader::new(stdout);
        let stderr_reader = AsyncBufReader::new(stderr);
        
        // Spawn tasks to handle output with live streaming
        let stdout_handle = tokio::spawn(Self::capture_output(
            stdout_reader, 
            stdout_writer, 
            pb.clone(), 
            tool.name.clone(), 
            false,
            progress_manager.clone(),
            stdout_file.clone()
        ));
        let stderr_handle = tokio::spawn(Self::capture_output(
            stderr_reader, 
            stderr_writer, 
            pb.clone(), 
            tool.name.clone(), 
            true,
            progress_manager.clone(),
            stderr_file.clone()
        ));
        
        // Wait for process with timeout
        let timeout_duration = Duration::from_secs(tool.timeout);
        let exit_status = match timeout(timeout_duration, child.wait()).await {
            Ok(Ok(status)) => status,
            Ok(Err(e)) => {
                Self::write_log(&log_file, &format!("Tool {} failed: {}", tool.name, e)).await?;
                return Err(e.into());
            }
            Err(_) => {
                Self::write_log(&log_file, &format!("Tool {} timed out after {}s", tool.name, tool.timeout)).await?;
                child.kill().await?;
                return Err(format!("Tool {} timed out", tool.name).into());
            }
        };
        
        // Wait for output capture to complete
        let _ = stdout_handle.await;
        let _ = stderr_handle.await;
        
        let duration = start.elapsed();
        let exit_code = exit_status.code().unwrap_or(-1);
        
        // Check if output file has content
        let metadata = fs::metadata(&stdout_file)?;
        let has_output = metadata.len() > 0;
        
        let error = if !exit_status.success() {
            Some(format!("Exit code: {}", exit_code))
        } else {
            None
        };
        
        Self::write_log(&log_file, &format!("Tool {} completed in {:?} with exit code {}", tool.name, duration, exit_code)).await?;
        
        Ok(ToolResult {
            tool_name: tool.name,
            exit_code,
            stdout_file,
            stderr_file,
            duration,
            has_output,
            error,
        })
    }

    async fn capture_output(
        reader: AsyncBufReader<impl tokio::io::AsyncRead + Unpin>,
        mut writer: impl AsyncWriteExt + Unpin,
        pb: ProgressBar,
        tool_name: String,
        is_stderr: bool,
        _progress_manager: Arc<ProgressManager>,
        _output_file: PathBuf,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut lines = reader.lines();
        let mut line_count = 0;
        // Discovery tracking removed - will be handled by parser after execution
        
        while let Some(line) = lines.next_line().await? {
            writer.write_all(line.as_bytes()).await?;
            writer.write_all(b"\n").await?;
            line_count += 1;
            
            // Update progress display only (no parsing here)
            if !is_stderr {
                // Show progress with line preview
                if line_count % 3 == 0 {
                    let preview = if line.len() > 50 { 
                        format!("{}...", &line[..47])
                    } else { 
                        line.clone() 
                    };
                    pb.set_message(format!("{}: {}", tool_name, preview));
                } else if line_count == 1 {
                    pb.set_message(format!("{}: scanning", tool_name));
                }
            } else {
                // For stderr, show error output occasionally
                if line_count % 5 == 0 {
                    pb.set_message(format!("{}: stderr output", tool_name));
                }
            }
        }
        
        // Discovery counters already updated in real-time above
        // No need to add again at the end to avoid double-counting
        
        writer.flush().await?;
        Ok(())
    }

    async fn write_log(log_file: &Arc<Mutex<File>>, message: &str) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut file = log_file.lock().await;
        writeln!(file, "[{}] {}", timestamp(), message)?;
        file.flush()?;
        Ok(())
    }

    async fn log_info(&self, message: &str) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Self::write_log(&self.log_file, &format!("INFO: {}", message)).await
    }

    async fn log_warning(&self, message: &str) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Self::write_log(&self.log_file, &format!("WARN: {}", message)).await
    }

    async fn log_error(&self, message: &str) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Self::write_log(&self.log_file, &format!("ERROR: {}", message)).await
    }


    pub fn print_summary(&self, results: &[ToolResult]) {
        let successful = results.iter().filter(|r| r.exit_code == 0).count();
        let failed = results.iter().filter(|r| r.exit_code != 0).count();
        let total_duration: Duration = results.iter().map(|r| r.duration).sum();
        
        self.progress_manager.print_section(&format!(
            "Summary: {} passed, {} failed in {:.1}s",
            successful, failed, total_duration.as_secs_f64()
        ));
        
        if failed > 0 {
            self.progress_manager.print_warning("Failed tools:");
            for result in results.iter().filter(|r| r.exit_code != 0) {
                self.progress_manager.print_error(&format!("  {}", result.tool_name));
            }
        }
        
        // Add error summary if there are logged errors
        if self.error_handler.has_errors() {
            if let Ok(error_summary) = self.error_handler.create_error_summary() {
                self.progress_manager.print_warning("Error details logged - see full summary below:");
                println!("{}", error_summary);
            }
        }
    }
}

impl Clone for ExecutionContext {
    fn clone(&self) -> Self {
        Self {
            output_dir: self.output_dir.clone(),
            target: self.target.clone(),
            debug: self.debug,
            verbose: self.verbose,
        }
    }
}

fn timestamp() -> String {
    Local::now().format("%Y-%m-%d %H:%M:%S").to_string()
}