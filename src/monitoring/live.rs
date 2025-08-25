use std::collections::HashMap;
use std::time::{Duration, Instant};
use sysinfo::System;
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::Mutex;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};

pub struct LiveMonitor {
    active_processes: HashMap<u32, ProcessInfo>,
    completed_tasks: Vec<CompletedTask>,
    multi_progress: MultiProgress,
    main_progress: ProgressBar,
    plugin_progress: HashMap<String, ProgressBar>,
    total_tasks: usize,
    completed_count: Arc<Mutex<usize>>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct ProcessInfo {
    pub pid: u32,
    pub command: String,
    pub plugin_name: String,
    pub start_time: Instant,
    pub cpu_usage: f32,
    pub memory_usage: u64,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct CompletedTask {
    pub plugin_name: String,
    pub duration: Duration,
    pub success: bool,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct DisplayStats {
    pub system_cpu: f32,
    pub system_memory_used: u64,
    pub system_memory_total: u64,
    pub file_descriptors_used: usize,
    pub file_descriptors_limit: usize,
    pub active_processes: Vec<ProcessInfo>,
    pub completed_tasks: Vec<CompletedTask>,
    pub elapsed_time: Duration,
}

impl LiveMonitor {
    pub fn new() -> Self {
        let multi_progress = MultiProgress::new();
        let main_progress = multi_progress.add(ProgressBar::new(100));
        
        // Set up main progress bar style
        main_progress.set_style(
            ProgressStyle::default_bar()
                .template("┌─ {msg} [{wide_bar:.cyan/blue}] {percent}% │ {pos}/{len} tasks │ {elapsed_precise}")
                .unwrap()
                .progress_chars("█▉▊▋▌▍▎▏ ")
        );
        
        Self {
            active_processes: HashMap::new(),
            completed_tasks: Vec::new(),
            multi_progress,
            main_progress,
            plugin_progress: HashMap::new(),
            total_tasks: 0,
            completed_count: Arc::new(Mutex::new(0)),
        }
    }

    #[allow(dead_code)]
    pub fn track_process_start(&mut self, pid: u32, command: String, plugin_name: String) {
        let process_info = ProcessInfo {
            pid,
            command,
            plugin_name,
            start_time: Instant::now(),
            cpu_usage: 0.0,
            memory_usage: 0,
        };
        
        self.active_processes.insert(pid, process_info);
    }

    #[allow(dead_code)]
    pub fn track_process_end(&mut self, pid: u32, success: bool) {
        if let Some(process_info) = self.active_processes.remove(&pid) {
            let duration = process_info.start_time.elapsed();
            let completed_task = CompletedTask {
                plugin_name: process_info.plugin_name,
                duration,
                success,
            };
            self.completed_tasks.push(completed_task);
        }
    }

    #[allow(dead_code)]
    pub async fn track_task<F, Fut, T>(&mut self, plugin_name: &str, future: F) -> Result<T>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        let start_time = Instant::now();
        tracing::info!("Starting monitored task: {}", plugin_name);
        
        let result = future().await;
        let duration = start_time.elapsed();
        
        let completed_task = CompletedTask {
            plugin_name: plugin_name.to_string(),
            duration,
            success: result.is_ok(),
        };
        
        self.completed_tasks.push(completed_task);
        
        match &result {
            Ok(_) => tracing::info!("Completed task: {} in {:.1}s", plugin_name, duration.as_secs_f32()),
            Err(e) => tracing::error!("Failed task: {} after {:.1}s: {}", plugin_name, duration.as_secs_f32(), e),
        }
        
        result
    }



    pub async fn initialize_progress(&mut self, target: &str, total_tasks: usize) {
        self.total_tasks = total_tasks;
        
        // Set main progress bar
        self.main_progress.set_length(total_tasks as u64);
        self.main_progress.set_position(0);
        self.main_progress.set_message(target.to_string());
        
        // Reset completed count
        *self.completed_count.lock().await = 0;
    }
    
    pub fn add_plugin_progress(&mut self, plugin_name: &str) -> ProgressBar {
        let pb = self.multi_progress.add(ProgressBar::new_spinner());
        pb.set_style(
            ProgressStyle::default_spinner()
                .template("└─ {spinner:.green} {msg}")
                .unwrap()
                .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈")
        );
        pb.set_message(format!("{} (initializing)", plugin_name));
        pb.enable_steady_tick(Duration::from_millis(100));
        
        self.plugin_progress.insert(plugin_name.to_string(), pb.clone());
        pb
    }
    
    pub fn update_plugin_progress(&self, plugin_name: &str, status: &str) {
        if let Some(pb) = self.plugin_progress.get(plugin_name) {
            pb.set_message(format!("{} ({})", plugin_name, status));
        }
    }
    
    
    pub fn start_system_stats_update(&self) -> tokio::task::JoinHandle<()> {
        let multi = self.multi_progress.clone();
        let stats_pb = multi.add(ProgressBar::new_spinner());
        
        stats_pb.set_style(
            ProgressStyle::default_spinner()
                .template("└─ {msg}")
                .unwrap()
        );
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(500));
            let mut system = System::new_all();
            
            loop {
                interval.tick().await;
                system.refresh_cpu();
                system.refresh_memory();
                
                let memory_gb = system.used_memory() as f64 / 1024.0 / 1024.0 / 1024.0;
                let memory_total_gb = system.total_memory() as f64 / 1024.0 / 1024.0 / 1024.0;
                
                stats_pb.set_message(format!(
                    "System: CPU:{:.1}% RAM:{:.1}GB/{:.1}GB FD:0/1024",
                    system.global_cpu_info().cpu_usage(),
                    memory_gb,
                    memory_total_gb
                ));
            }
        })
    }

    pub fn finish_all(&self) {
        self.main_progress.finish_with_message("All tasks completed");
        
        // Finish any remaining plugin progress bars
        for (_, pb) in &self.plugin_progress {
            if !pb.is_finished() {
                pb.finish();
            }
        }
    }
    
    pub fn get_multi_progress(&self) -> MultiProgress {
        self.multi_progress.clone()
    }

    #[allow(dead_code)]
    pub fn start_live_updates(&mut self, _target: String, _active_count: usize, _total_count: usize) -> tokio::task::JoinHandle<()> {
        // This is a bit tricky because we need to share self between the task and the caller
        // For now, return a simple handle. We'll improve this in integration
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(200));
            loop {
                interval.tick().await;
                // TODO: Update display here
                // This requires restructuring to share state properly
            }
        })
    }
}

impl Default for LiveMonitor {
    fn default() -> Self {
        Self::new()
    }
}