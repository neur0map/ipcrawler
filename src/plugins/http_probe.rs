use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::RunState};
use crate::executors::command::execute;
use crate::plugins::types::ServiceScan;
use crate::config::GlobalConfig;

pub struct HttpProbe;

impl HttpProbe {
    fn write_plugin_results(&self, service: &Service, url: &str, success: bool, scans_dir: &std::path::Path) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== {} Results ===\n", self.name()));
        content.push_str(&format!("HTTP probe for {}:{}\n", service.address, service.port));
        content.push_str(&format!("URL: {}\n", url));
        content.push_str(&format!("Status: {}\n", if success { "SUCCESS" } else { "FAILED" }));
        content.push_str(&format!("Service: {} ({:?})\n", service.name, service.proto));
        content.push_str(&format!("Secure: {}\n", service.secure));
        content.push_str(&format!("Timestamp: {}\n", chrono::Utc::now()));
        
        let result_file = scans_dir.join(format!("http_probe_{}_{}_results.txt", service.address, service.port));
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        
        Ok(())
    }
}

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

    async fn run(&self, service: &Service, state: &RunState, config: &GlobalConfig) -> Result<()> {
        let dirs = state.dirs.as_ref().unwrap();
        let scheme = if service.secure || service.port == 443 { "https" } else { "http" };
        let url = format!("{}://{}:{}", scheme, service.address, service.port);
        let output_file = dirs.scans.join(format!("http_{}_{}.txt", service.address, service.port));
        
        let mut args = config.tools.http_probe.base_args.clone();
        
        // Add timeout settings
        args.extend(vec![
            "--connect-timeout".to_string(),
            config.tools.http_probe.options.connect_timeout_s.to_string(),
            "--max-time".to_string(),
            config.tools.http_probe.options.max_time_s.to_string(),
        ]);
        
        // Add redirect settings
        if config.tools.http_probe.options.follow_redirects {
            if !args.contains(&"-L".to_string()) {
                args.push("-L".to_string());
            }
            args.extend(vec![
                "--max-redirs".to_string(),
                config.tools.http_probe.options.max_redirects.to_string(),
            ]);
        }
        
        // Add SSL settings
        if !config.tools.http_probe.ssl.verify_cert {
            args.push("-k".to_string());
        }
        
        // Add user agent if configured
        if !config.tools.http_probe.options.user_agent.is_empty() {
            args.extend(vec![
                "-A".to_string(),
                config.tools.http_probe.options.user_agent.clone(),
            ]);
        }
        
        // Add verbose mode if configured
        if config.tools.http_probe.output.verbose {
            args.push("-v".to_string());
        }
        
        // Add output file
        args.extend(vec![
            "-o".to_string(),
            output_file.to_str().unwrap().to_string(),
        ]);
        
        args.push(url.clone());
        
        // Convert to &str for execute function
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let command = &config.tools.http_probe.command;
        let timeout = Some(config.tools.http_probe.limits.timeout_ms);
        let success = match execute(command, &args_str, &dirs.scans, timeout).await {
            Ok(_) => {
                tracing::info!("HTTP probe successful for {}", url);
                true
            }
            Err(e) => {
                tracing::warn!("HTTP probe failed for {}: {}", url, e);
                false
            }
        };
        
        // Write individual plugin result file
        self.write_plugin_results(service, &url, success, &dirs.scans)?;
        
        Ok(())
    }
}
