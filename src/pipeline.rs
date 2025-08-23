use crate::config::{Config, Tool, Chain};
use crate::executor::{ToolResult, ExecutionContext, Executor};
use crate::progress::ProgressManager;
use crate::gradient::{gradient_ports, gradient_tool};
use std::collections::HashMap;
use std::fs;
use std::sync::Arc;

pub struct Pipeline {
    config: Config,
    context: ExecutionContext,
    progress_manager: Arc<ProgressManager>,
    emergency_stop: bool,
    notifications: bool,
}

impl Pipeline {
    pub fn new(config: Config, context: ExecutionContext, progress_manager: Arc<ProgressManager>, emergency_stop: bool, notifications: bool) -> Self {
        Self { config, context, progress_manager, emergency_stop, notifications }
    }

    pub async fn execute_with_chaining(&mut self) -> Result<Vec<ToolResult>, Box<dyn std::error::Error + Send + Sync>> {
        // Clean start - let the tools speak for themselves
        
        let mut completed_tools: HashMap<String, ToolResult> = HashMap::new();
        let mut remaining_tools: Vec<Tool> = self.config.tools.clone()
            .into_iter()
            .filter(|t| t.enabled)
            .collect();
        
        // Create discovery tracking (keep only essential info)
        let discovery_bar = self.progress_manager.create_discovery_bar();
        
        // Track which tools are waiting for dependencies
        let dependency_map = self.build_dependency_map();
        
        while !remaining_tools.is_empty() {
            let mut ready_tools = Vec::new();
            let mut waiting_tools = Vec::new();
            
            // Separate tools that are ready to run vs waiting for dependencies
            for tool in remaining_tools.into_iter() {
                if self.is_tool_ready(&tool, &completed_tools, &dependency_map) {
                    ready_tools.push(tool);
                } else {
                    waiting_tools.push(tool);
                }
            }
            
            if ready_tools.is_empty() {
                self.progress_manager.print_warning("No tools ready - dependency issue");
                discovery_bar.finish();
                break;
            }
            
            // Show queue status: ready tools and waiting tools
            let ready_names: Vec<String> = ready_tools.iter().map(|t| t.name.clone()).collect();
            let waiting_names: Vec<String> = waiting_tools.iter().map(|t| t.name.clone()).collect();
            
            if !waiting_names.is_empty() {
                self.progress_manager.print_verbose_info(&format!("Running: {} | Waiting: {}", 
                    ready_names.join(", "),
                    waiting_names.join(", ")
                ), self.context.verbose);
            } else {
                self.progress_manager.print_verbose_info(&format!("Running: {}", 
                    ready_names.join(", ")
                ), self.context.verbose);
            }
            
            // Execute ready tools
            let mut executor = Executor::new(
                Config {
                    metadata: self.config.metadata.clone(),
                    tools: ready_tools.clone(),
                    chains: Vec::new(), // No chains for individual execution
                    globals: self.config.globals.clone(),
                },
                self.context.clone(),
                self.progress_manager.clone(),
                self.emergency_stop,
                self.notifications
            )?;
            
            let results = executor.execute_batch(&discovery_bar).await?;
            
            // Process results and update chained tools
            for result in results {
                self.process_tool_result(&result, &mut waiting_tools)?;
                completed_tools.insert(result.tool_name.clone(), result);
            }
            
            remaining_tools = waiting_tools;
        }
        
        // Finish discovery tracking
        discovery_bar.finish();
        
        Ok(completed_tools.into_values().collect())
    }
    
    fn build_dependency_map(&self) -> HashMap<String, Vec<String>> {
        let mut deps = HashMap::new();
        
        // Build from chains
        for chain in &self.config.chains {
            deps.entry(chain.to.clone())
                .or_insert_with(Vec::new)
                .push(chain.from.clone());
        }
        
        deps
    }
    
    fn is_tool_ready(&self, tool: &Tool, completed: &HashMap<String, ToolResult>, deps: &HashMap<String, Vec<String>>) -> bool {
        if let Some(dependencies) = deps.get(&tool.name) {
            for dep in dependencies {
                if !completed.contains_key(dep) {
                    return false;
                }
                
                // Check chain conditions
                if let Some(chain) = self.config.chains.iter().find(|c| c.from == *dep && c.to == tool.name) {
                    if let Some(dep_result) = completed.get(dep) {
                        if !self.evaluate_chain_condition(chain, dep_result) {
                            return false;
                        }
                    }
                }
            }
        }
        true
    }
    
    fn evaluate_chain_condition(&self, chain: &Chain, result: &ToolResult) -> bool {
        match chain.condition.as_str() {
            "has_output" => result.has_output,
            "exit_success" => result.exit_code == 0,
            "file_size" => {
                if let Ok(metadata) = fs::metadata(&result.stdout_file) {
                    metadata.len() > 0
                } else {
                    false
                }
            }
            condition if condition.starts_with("contains:") => {
                let search_text = condition.strip_prefix("contains:").unwrap_or("");
                if let Ok(content) = fs::read_to_string(&result.stdout_file) {
                    content.contains(search_text)
                } else {
                    false
                }
            }
            _ => {
                self.progress_manager.print_warning(&format!("Unknown chain condition: {}", chain.condition));
                false
            }
        }
    }
    
    fn process_tool_result(&self, result: &ToolResult, waiting_tools: &mut Vec<Tool>) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // Find tools that depend on this result
        for chain in &self.config.chains {
            if chain.from == result.tool_name {
                if let Some(target_tool) = waiting_tools.iter_mut().find(|t| t.name == chain.to) {
                    if self.evaluate_chain_condition(chain, result) {
                        self.progress_manager.print_verbose_info(&format!("Chain: {} → {}", chain.from, chain.to), self.context.verbose);
                        
                        // Update target tool command with discovered data
                        self.update_tool_with_chain_data(target_tool, result)?;
                    } else {
                        self.progress_manager.print_verbose_info(&format!("Skip chain: {} → {} (condition not met)", chain.from, chain.to), self.context.verbose);
                    }
                }
            }
        }
        Ok(())
    }
    
    fn update_tool_with_chain_data(&self, tool: &mut Tool, source_result: &ToolResult) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // Generic approach: Check if tool command contains {discovered_ports} placeholder
        if tool.command.contains("{discovered_ports}") {
            // Parse ports from the source tool's output
            let ports = self.parse_discovered_ports(&source_result.stdout_file)?;
            
            if !ports.is_empty() {
                let port_list = ports.join(",");
                tool.command = tool.command.replace("{discovered_ports}", &port_list);
                // Always show port passing (not just in verbose mode) - this is important info
                let colored_ports = gradient_ports(&port_list);
                self.progress_manager.print_info(&format!("Passing {} discovered ports from {} → {}: {}", ports.len(), gradient_tool(&source_result.tool_name), gradient_tool(&tool.name), colored_ports));
                
                // Log the actual command for debugging
                if self.context.debug {
                    self.progress_manager.print_verbose_info(&format!("Updated command: {}", tool.command), true);
                }
            } else {
                // If no ports found but tool expects them, warn and disable
                self.progress_manager.print_warning(&format!("No ports found from {} → {} (disabling tool)", source_result.tool_name, tool.name));
                tool.enabled = false;
            }
        }
        
        Ok(())
    }
    
    fn parse_discovered_ports(&self, file_path: &std::path::PathBuf) -> Result<Vec<String>, Box<dyn std::error::Error + Send + Sync>> {
        let content = fs::read_to_string(file_path)?;
        let mut ports = Vec::new();
        
        // Generic port parsing - works with various output formats
        
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            
            // Try multiple common port output formats:
            // Format 1: "host:port" (naabu style)
            if let Some(port_part) = line.split(':').last() {
                if let Ok(port_num) = port_part.parse::<u16>() {
                    ports.push(port_num.to_string());
                    continue;
                }
            }
        }
        
        // Remove duplicates and sort efficiently
        let mut parsed_ports: Vec<u16> = ports
            .into_iter()
            .filter_map(|p| p.parse::<u16>().ok())
            .collect();
        parsed_ports.sort_unstable();
        parsed_ports.dedup();
        let ports: Vec<String> = parsed_ports.into_iter().map(|p| p.to_string()).collect();
        
        Ok(ports)
    }
}