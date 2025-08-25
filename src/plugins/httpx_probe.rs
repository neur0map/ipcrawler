use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::RunState};
use crate::executors::command::execute;
use crate::plugins::types::ServiceScan;
use crate::config::GlobalConfig;

#[derive(Clone)]
pub struct HttpxProbe;

impl HttpxProbe {
    fn write_plugin_results(&self, service: &Service, url: &str, success: bool, scans_dir: &std::path::Path) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== {} Results ===\n", self.name()));
        content.push_str(&format!("HTTPX probe for {}:{}\n", service.address, service.port));
        content.push_str(&format!("URL: {}\n", url));
        content.push_str(&format!("Status: {}\n", if success { "SUCCESS" } else { "FAILED" }));
        content.push_str(&format!("Service: {} ({:?})\n", service.name, service.proto));
        content.push_str(&format!("Secure: {}\n", service.secure));
        content.push_str(&format!("Timestamp: {}\n", chrono::Utc::now()));
        
        let result_file = scans_dir.join(format!("httpx_probe_{}_{}_results.txt", service.address, service.port));
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        
        Ok(())
    }
}

#[async_trait]
impl ServiceScan for HttpxProbe {
    fn name(&self) -> &'static str {
        "httpx_probe"
    }

    fn matches(&self, service: &Service) -> bool {
        service.name.contains("http") || 
        service.port == 80 || 
        service.port == 443 ||
        service.port == 8080 ||
        service.port == 8443 ||
        service.port == 8000 ||
        service.port == 8888 ||
        service.port == 3000 ||
        service.port == 5000 ||
        service.port == 9000
    }

    async fn run(&self, service: &Service, state: &RunState, config: &GlobalConfig) -> Result<()> {
        let dirs = state.dirs.as_ref().unwrap();
        let url = format!("{}:{}", service.address, service.port);
        let output_file = dirs.scans.join(format!("httpx_{}_{}.txt", service.address, service.port));
        
        let mut args = config.tools.httpx.base_args.clone();
        
        // Add httpx-specific flags (ProjectDiscovery syntax)
        args.extend(vec![
            "-u".to_string(), format!("http://{}:{}", service.address, service.port),
            "-o".to_string(), output_file.to_str().unwrap().to_string(),
            "-timeout".to_string(), config.tools.httpx.options.timeout_s.to_string(),
            "-retries".to_string(), config.tools.httpx.limits.max_retries.to_string(),
        ]);
        
        // Add probing options
        if config.tools.httpx.options.probe_all_ips {
            args.push("-probe-all-ips".to_string());
        }
        
        if config.tools.httpx.options.follow_redirects {
            args.push("-follow-redirects".to_string());
        }
        
        if config.tools.httpx.options.follow_host_redirects {
            args.push("-follow-host-redirects".to_string());
        }
        
        // Add output options
        if config.tools.httpx.output.status_code {
            args.push("-status-code".to_string());
        }
        
        if config.tools.httpx.output.content_length {
            args.push("-content-length".to_string());
        }
        
        if config.tools.httpx.output.title {
            args.push("-title".to_string());
        }
        
        if config.tools.httpx.output.tech_detect {
            args.push("-tech-detect".to_string());
        }
        
        if config.tools.httpx.output.server {
            args.push("-server".to_string());
        }
        
        // Add content type detection
        if config.tools.httpx.output.content_type {
            args.push("-content-type".to_string());
        }
        
        // Add method
        if !config.tools.httpx.options.method.is_empty() {
            args.extend(vec!["-method".to_string(), config.tools.httpx.options.method.clone()]);
        }
        
        // Add user agent
        if !config.tools.httpx.options.user_agent.is_empty() {
            args.extend(vec!["-H".to_string(), format!("User-Agent: {}", config.tools.httpx.options.user_agent)]);
        }
        
        // Convert to &str for execute function
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let command = &config.tools.httpx.command;
        let timeout = Some(config.tools.httpx.limits.timeout_ms);
        
        let success = match execute(command, &args_str, &dirs.scans, timeout).await {
            Ok(_) => {
                tracing::info!("HTTPX probe successful for {}", url);
                true
            }
            Err(e) => {
                tracing::warn!("HTTPX probe failed for {}: {}", url, e);
                false
            }
        };
        
        // Write individual plugin result file
        self.write_plugin_results(service, &url, success, &dirs.scans)?;
        
        Ok(())
    }
}
