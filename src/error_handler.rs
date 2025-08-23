use crate::progress::ProgressManager;
use chrono::Local;
use colored::*;
#[cfg(feature = "notify-rust")]
use notify_rust::Notification;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct ErrorContext {
    pub tool_name: String,
    pub error_message: String,
    pub exit_code: Option<i32>,
    pub timestamp: chrono::DateTime<chrono::Local>,
    pub command: String,
    pub output_file: Option<PathBuf>,
}

#[derive(Clone)]
pub struct ErrorHandler {
    progress_manager: Arc<ProgressManager>,
    error_log_path: PathBuf,
    emergency_stop_enabled: bool,
    notifications_enabled: bool,
}

impl ErrorHandler {
    pub fn new(
        progress_manager: Arc<ProgressManager>,
        output_dir: &PathBuf,
        emergency_stop: bool,
        notifications: bool,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let error_log_path = output_dir.join("errors.log");

        // Create error log file with header
        let mut error_file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&error_log_path)?;

        writeln!(
            error_file,
            "\n=== ipcrawler Error Log - {} ===",
            Local::now().format("%Y-%m-%d %H:%M:%S")
        )?;

        Ok(Self {
            progress_manager,
            error_log_path,
            emergency_stop_enabled: emergency_stop,
            notifications_enabled: notifications,
        })
    }

    pub async fn handle_tool_failure(
        &self,
        error_ctx: ErrorContext,
    ) -> Result<bool, Box<dyn std::error::Error + Send + Sync>> {
        // Log error to file
        self.log_error_to_file(&error_ctx).await?;

        // Display error to user
        self.display_error(&error_ctx);

        // Send notification if enabled
        if self.notifications_enabled {
            self.send_notification(&error_ctx);
        }

        // Determine if we should emergency stop
        let should_stop = self.should_emergency_stop(&error_ctx);

        if should_stop {
            self.trigger_emergency_stop(&error_ctx).await?;
        }

        Ok(should_stop)
    }

    async fn log_error_to_file(
        &self,
        error_ctx: &ErrorContext,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut error_file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.error_log_path)?;

        writeln!(
            error_file,
            "[{}] TOOL_FAILURE: {} (exit_code: {})",
            error_ctx.timestamp.format("%H:%M:%S"),
            error_ctx.tool_name,
            error_ctx
                .exit_code
                .map_or("unknown".to_string(), |c| c.to_string())
        )?;

        writeln!(error_file, "Command: {}", error_ctx.command)?;
        writeln!(error_file, "Error: {}", error_ctx.error_message)?;

        if let Some(output_file) = &error_ctx.output_file {
            writeln!(error_file, "Output file: {}", output_file.display())?;
        }

        writeln!(error_file, "---")?;

        Ok(())
    }

    fn display_error(&self, error_ctx: &ErrorContext) {
        self.progress_manager.print_error(&format!(
            "CRITICAL: {} failed (exit_code: {})",
            error_ctx.tool_name.red().bold(),
            error_ctx
                .exit_code
                .map_or("unknown".to_string(), |c| c.to_string())
                .red()
        ));

        self.progress_manager
            .print_error(&format!("Error: {}", error_ctx.error_message.yellow()));

        if self.emergency_stop_enabled {
            self.progress_manager.print_warning(&format!(
                "Emergency stop is {}. Scan will be terminated.",
                "ENABLED".red().bold()
            ));
        }
    }

    fn send_notification(&self, error_ctx: &ErrorContext) {
        #[cfg(feature = "notify-rust")]
        {
            let _ = Notification::new()
                .summary("ipcrawler - Tool Failure")
                .body(&format!(
                    "Tool '{}' failed with exit code {}.\nError: {}",
                    error_ctx.tool_name,
                    error_ctx
                        .exit_code
                        .map_or("unknown".to_string(), |c| c.to_string()),
                    error_ctx.error_message
                ))
                .icon("dialog-error")
                .timeout(10000) // 10 seconds
                .show();
        }
        #[cfg(not(feature = "notify-rust"))]
        {
            // Fallback: print notification info to console
            self.progress_manager.print_warning(&format!(
                "🔔 Desktop notification: Tool '{}' failed",
                error_ctx.tool_name
            ));
        }
    }

    fn should_emergency_stop(&self, error_ctx: &ErrorContext) -> bool {
        if !self.emergency_stop_enabled {
            return false;
        }

        // Define critical failure conditions
        match error_ctx.exit_code {
            Some(1) => true,         // General errors
            Some(2) => true,         // Misuse of shell builtins
            Some(126) => true,       // Command not executable
            Some(127) => true,       // Command not found
            Some(128..=255) => true, // Fatal error signals
            None => true,            // Process didn't exit cleanly
            _ => false,
        }
    }

    async fn trigger_emergency_stop(
        &self,
        error_ctx: &ErrorContext,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.progress_manager.print_error(&format!(
            "{} EMERGENCY STOP TRIGGERED {}",
            "🚨".repeat(3),
            "🚨".repeat(3)
        ));

        self.progress_manager.print_error(&format!(
            "Reason: Critical failure in tool '{}'",
            error_ctx.tool_name.red().bold()
        ));

        self.progress_manager
            .print_warning("All remaining tools will be cancelled.");
        self.progress_manager.print_warning(&format!(
            "Error details saved to: {}",
            self.error_log_path.display().to_string().cyan()
        ));

        // Log emergency stop
        let mut error_file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.error_log_path)?;

        writeln!(
            error_file,
            "[{}] EMERGENCY_STOP: Triggered by {} failure",
            Local::now().format("%H:%M:%S"),
            error_ctx.tool_name
        )?;

        // Send critical notification
        if self.notifications_enabled {
            #[cfg(feature = "notify-rust")]
            {
                let _ = Notification::new()
                    .summary("ipcrawler - EMERGENCY STOP")
                    .body(&format!(
                        "Critical failure in '{}' triggered emergency stop.\nAll remaining tools cancelled.",
                        error_ctx.tool_name
                    ))
                    .icon("dialog-error")
                    .urgency(notify_rust::Urgency::Critical)
                    .timeout(0) // No timeout - requires manual dismissal
                    .show();
            }
            #[cfg(not(feature = "notify-rust"))]
            {
                self.progress_manager.print_error(&format!(
                    "🚨 CRITICAL NOTIFICATION: Emergency stop triggered by '{}'",
                    error_ctx.tool_name
                ));
            }
        }

        Ok(())
    }

    pub fn create_error_summary(&self) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let log_content = std::fs::read_to_string(&self.error_log_path)
            .unwrap_or_else(|_| "No errors logged.".to_string());

        Ok(format!(
            "\n{}\nERROR SUMMARY\n{}\n\nError log location: {}\n\n{}",
            "=".repeat(50).red(),
            "=".repeat(50).red(),
            self.error_log_path.display().to_string().cyan(),
            log_content
        ))
    }

    pub fn has_errors(&self) -> bool {
        self.error_log_path.exists()
            && std::fs::metadata(&self.error_log_path)
                .map(|m| m.len() > 0)
                .unwrap_or(false)
    }
}

#[derive(Debug)]
pub struct EmergencyStopError {
    pub message: String,
    pub failed_tool: String,
}

impl std::fmt::Display for EmergencyStopError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Emergency stop: {} (failed tool: {})",
            self.message, self.failed_tool
        )
    }
}

impl std::error::Error for EmergencyStopError {}
