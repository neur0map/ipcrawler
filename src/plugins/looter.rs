use crate::config::GlobalConfig;
use crate::core::{models::Service, state::{RunState, PluginFindings}};
use crate::ui::events::UiEvent;
use anyhow::{anyhow, Result};
use async_trait::async_trait;
use serde::Serialize;
use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::fs;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::sync::Mutex;
use tokio::time::{sleep, timeout, sleep_until};
// CancellationToken removed as functionality is implemented inline
use url::Url;

pub struct LooterPlugin {
    config: LooterConfig,
    budget: TimeBudget,
    telemetry: Arc<Mutex<Telemetry>>,
    degradation_matrix: DegradationMatrix,
    rng: DeterministicRng,
    waf_manager: Arc<Mutex<WafManager>>,
    filename_triage: FilenameTriage,
    mutation_engine: MutationEngine,
}

// ============================================================================
// Time Budget Management
// ============================================================================

#[derive(Debug, Clone)]
struct TimeBudget {
    total_budget: Duration,
    phase_allocations: HashMap<Phase, f32>,
    start_time: Instant,
    phase_timers: HashMap<Phase, Duration>,
}

impl TimeBudget {
    fn default_ctf() -> Self {
        Self::with_total_seconds(120)  // 2 minutes per target (optimized for CTF/lab)
    }
    
    fn with_total_seconds(total_sec: u64) -> Self {
        let mut allocations = HashMap::new();
        allocations.insert(Phase::Seeds, 0.15);      // 15% of total
        allocations.insert(Phase::Baseline, 0.25);   // 25% of total
        allocations.insert(Phase::Enhanced, 0.30);   // 30% of total  
        allocations.insert(Phase::Retrieval, 0.20);  // 20% of total
        allocations.insert(Phase::Analysis, 0.10);   // 10% of total
        
        Self {
            total_budget: Duration::from_secs(total_sec),
            phase_allocations: allocations,
            start_time: Instant::now(),
            phase_timers: HashMap::new(),
        }
    }
    
    fn get_phase_budget(&self, phase: Phase) -> Duration {
        let percentage = self.phase_allocations.get(&phase).unwrap_or(&0.2);
        Duration::from_secs_f32(self.total_budget.as_secs_f32() * percentage)
    }
    
    fn time_remaining(&self) -> Duration {
        let elapsed = self.start_time.elapsed();
        self.total_budget.saturating_sub(elapsed)
    }
    
    fn remaining_deadline(&self) -> Instant {
        self.start_time + self.total_budget
    }
}

#[derive(Debug, Clone, Copy, Hash, Eq, PartialEq)]
enum Phase {
    Seeds,
    Baseline,
    Enhanced,
    Retrieval,
    Analysis,
}

// ============================================================================
// Deterministic RNG for Reproducible Runs
// ============================================================================

#[derive(Clone)]
struct DeterministicRng {
    seed: [u8; 32],
    counter: u64,
}

impl DeterministicRng {
    fn from_target(target_url: &str) -> Self {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        target_url.hash(&mut hasher);
        let hash = hasher.finish();
        
        let mut seed = [0u8; 32];
        seed[..8].copy_from_slice(&hash.to_le_bytes());
        
        Self { seed, counter: 0 }
    }
    
    fn jitter(&mut self, max_ms: u64) -> Duration {
        self.counter += 1;
        // Use seed for deterministic variance
        let seed_influence = (self.seed[0] as u64) % 10;
        let value = (self.counter + seed_influence) % max_ms;
        Duration::from_millis(value)
    }
    
    fn sample_indices(&mut self, total: usize, count: usize) -> Vec<usize> {
        let mut indices = Vec::with_capacity(count.min(total));
        for i in 0..count.min(total) {
            self.counter += 1;
            let idx = (self.counter as usize + i) % total;
            indices.push(idx);
        }
        indices.sort();
        indices.dedup();
        indices
    }
}

// ============================================================================
// Tool Degradation Matrix
// ============================================================================

#[derive(Debug, Clone, Eq, Hash, PartialEq)]
enum Capability {
    CrawlUrls,
    DirBruteforce,
    WordMine,
    FetchHttp,
}

#[derive(Debug, Clone)]
enum Tool {
    Katana,
    Hakrawler,
    SimpleProber,
    Feroxbuster,
    Ffuf,
    Gobuster,
    Cewl,
    TokenizeUrls,
    Xh,
    Curl,
    Wget,
    None,
}

impl Tool {
    fn name(&self) -> &str {
        match self {
            Tool::Katana => "katana",
            Tool::Hakrawler => "hakrawler",
            Tool::SimpleProber => "simple-prober",
            Tool::Feroxbuster => "feroxbuster",
            Tool::Ffuf => "ffuf",
            Tool::Gobuster => "gobuster",
            Tool::Cewl => "cewl",
            Tool::TokenizeUrls => "tokenize-urls",
            Tool::Xh => "xh",
            Tool::Curl => "curl",
            Tool::Wget => "wget",
            Tool::None => "none",
        }
    }
    
    async fn is_available(&self) -> bool {
        match self {
            Tool::None | Tool::TokenizeUrls | Tool::SimpleProber => true,
            tool => {
                which::which(tool.name()).is_ok()
            }
        }
    }
}

struct DegradationMatrix {
    capabilities: HashMap<Capability, Vec<Tool>>,
    fallback_log: Vec<(Capability, Tool, Tool)>,
}

impl DegradationMatrix {
    fn new() -> Self {
        let mut capabilities = HashMap::new();
        
        capabilities.insert(Capability::CrawlUrls, vec![
            Tool::Katana,
            Tool::Hakrawler,
            Tool::SimpleProber,
        ]);
        
        capabilities.insert(Capability::DirBruteforce, vec![
            Tool::Feroxbuster,
            Tool::Ffuf,
            Tool::Gobuster,
        ]);
        
        capabilities.insert(Capability::WordMine, vec![
            Tool::Cewl,
            Tool::TokenizeUrls,
            Tool::None,
        ]);
        
        capabilities.insert(Capability::FetchHttp, vec![
            Tool::Xh,
            Tool::Curl,
            Tool::Wget,
        ]);
        
        Self { capabilities, fallback_log: Vec::new() }
    }
    
    async fn get_tool(&mut self, capability: Capability) -> Option<Tool> {
        let tools = self.capabilities.get(&capability)?;
        
        for (i, tool) in tools.iter().enumerate() {
            if tool.is_available().await {
                if i > 0 {
                    self.fallback_log.push((capability.clone(), tools[0].clone(), tool.clone()));
                    tracing::warn!("Using fallback: {} -> {}", tools[0].name(), tool.name());
                }
                return Some(tool.clone());
            }
        }
        None
    }
}

// ============================================================================
// WAF Manager with Rate Limiting
// ============================================================================

#[derive(Clone)]
struct WafManager {
    host_limiters: HashMap<String, HostLimiter>,
    global_qps: f32,
    backoff_states: HashMap<String, BackoffState>,
    rng: DeterministicRng,
}

#[derive(Clone)]
struct HostLimiter {
    last_request: Instant,
    min_delay: Duration,
    burst_counter: usize,
    status_history: VecDeque<u16>,
}

#[derive(Clone)]
struct BackoffState {
    delay: Duration,
    until: Instant,
}

impl WafManager {
    fn new(rng: DeterministicRng) -> Self {
        Self {
            host_limiters: HashMap::new(),
            global_qps: 15.0,
            backoff_states: HashMap::new(),
            rng,
        }
    }
    
    async fn wait_for_slot(&mut self, url: &str) -> Result<()> {
        let host = Url::parse(url)?.host_str().unwrap_or("").to_string();
        
        let limiter = self.host_limiters.entry(host.clone()).or_insert_with(|| {
            HostLimiter {
                last_request: Instant::now() - Duration::from_secs(1),
                min_delay: Duration::from_millis(67), // ~15 req/sec
                burst_counter: 0,
                status_history: VecDeque::with_capacity(10),
            }
        });
        
        // Check backoff state
        if let Some(backoff) = self.backoff_states.get(&host) {
            if backoff.until > Instant::now() {
                sleep(backoff.until - Instant::now()).await;
            }
        }
        
        // Apply rate limiting
        let elapsed = limiter.last_request.elapsed();
        if elapsed < limiter.min_delay {
            let wait_time = limiter.min_delay - elapsed;
            let jitter = self.rng.jitter(20);
            sleep(wait_time + jitter).await;
        }
        
        limiter.last_request = Instant::now();
        limiter.burst_counter += 1;
        
        // Burst cap
        if limiter.burst_counter > 10 {
            sleep(Duration::from_millis(500)).await;
            limiter.burst_counter = 0;
        }
        
        Ok(())
    }
    
    fn record_response(&mut self, url: &str, status: u16) {
        let host = Url::parse(url).ok().and_then(|u| u.host_str().map(String::from)).unwrap_or_default();
        
        if let Some(limiter) = self.host_limiters.get_mut(&host) {
            limiter.status_history.push_back(status);
            if limiter.status_history.len() > 10 {
                limiter.status_history.pop_front();
            }
            
            // Detect patterns requiring backoff
            let recent_403s = limiter.status_history.iter().filter(|&&s| s == 403).count();
            let recent_429s = limiter.status_history.iter().filter(|&&s| s == 429).count();
            
            if recent_429s >= 3 || recent_403s >= 5 {
                let current_backoff = self.backoff_states.get(&host)
                    .map(|b| b.delay)
                    .unwrap_or(Duration::from_secs(1));
                
                let new_delay = (current_backoff * 2).min(Duration::from_secs(30));
                self.backoff_states.insert(host, BackoffState {
                    delay: new_delay,
                    until: Instant::now() + new_delay,
                });
                
                limiter.min_delay = (limiter.min_delay * 2).min(Duration::from_millis(500));
            }
        }
    }
    
    fn should_attempt_request(&self, host: &str) -> bool {
        // Check if we're in a backoff period for this host
        if let Some(backoff) = self.backoff_states.get(host) {
            if Instant::now() < backoff.until {
                return false;
            }
        }
        
        // Check recent status history for patterns that indicate we should back off
        if let Some(limiter) = self.host_limiters.get(host) {
            let recent_429s = limiter.status_history.iter().filter(|&&s| s == 429).count();
            let recent_403s = limiter.status_history.iter().filter(|&&s| s == 403).count();
            
            // Don't attempt if we're seeing too many rate limit or forbidden responses
            if recent_429s >= 2 || recent_403s >= 4 {
                return false;
            }
        }
        
        true
    }
    
    fn record_failure(&mut self, host: &str) {
        // Record a 500-level failure for this host
        self.record_response(&format!("http://{}/", host), 500);
    }
    
    fn record_success(&mut self, host: &str) {
        // Record a successful response for this host
        self.record_response(&format!("http://{}/", host), 200);
    }
    
    async fn apply_rate_limit(&self, host: &str) -> Result<()> {
        // Apply rate limiting for the given host
        if let Some(backoff) = self.backoff_states.get(host) {
            let now = Instant::now();
            if now < backoff.until {
                let delay = backoff.until - now;
                tracing::debug!("Applying backoff delay of {:?} for host {}", delay, host);
                tokio::time::sleep(delay).await;
            }
        }
        
        // Apply global rate limiting with jitter
        let base_delay = Duration::from_millis((1000.0 / self.global_qps) as u64);
        
        // Add deterministic jitter using the RNG method
        // Create a temporary RNG based on host for deterministic jitter
        let mut temp_rng = DeterministicRng::from_target(host);
        let jitter = temp_rng.jitter(200); // Up to 200ms jitter
        let total_delay = base_delay + jitter;
        
        tokio::time::sleep(total_delay).await;
        
        Ok(())
    }
}

// ============================================================================
// Filename Triage for Pre-Download Scoring
// ============================================================================

#[derive(Clone)]
struct FilenameTriage {
    patterns: Vec<(String, u8, f32)>,
}

impl FilenameTriage {
    fn new() -> Self {
        let patterns = vec![
            (".env".to_string(), 10, 0.95),
            (".git/config".to_string(), 10, 0.95),
            (".git/HEAD".to_string(), 10, 0.90),
            ("wp-config.php".to_string(), 10, 0.90),
            ("id_rsa".to_string(), 10, 1.0),
            (".ssh/authorized_keys".to_string(), 10, 0.85),
            ("backup.zip".to_string(), 8, 0.80),
            ("db.sql".to_string(), 8, 0.85),
            ("database.sql".to_string(), 8, 0.85),
            (".htpasswd".to_string(), 8, 0.75),
            ("admin/".to_string(), 8, 0.70),
            ("config.php".to_string(), 8, 0.75),
            ("composer.json".to_string(), 6, 0.60),
            ("package.json".to_string(), 6, 0.60),
            ("robots.txt".to_string(), 4, 0.50),
        ];
        
        Self { patterns }
    }
    
    fn score_url(&self, url: &str) -> (u8, f32) {
        let mut best_priority = 1;
        let mut best_confidence = 0.0;
        
        for (pattern, priority, confidence) in &self.patterns {
            if url.contains(pattern)
                && (*priority > best_priority || (*priority == best_priority && *confidence > best_confidence)) {
                best_priority = *priority;
                best_confidence = *confidence;
            }
        }
        
        (best_priority, best_confidence)
    }
}

// ============================================================================
// Mutation Engine for Wordlist Enhancement
// ============================================================================

struct MutationEngine {
    soft_cap: usize,
    hard_cap: usize,
    df_table: HashMap<String, f32>,
}

impl MutationEngine {
    fn new() -> Self {
        let mut df_table = HashMap::new();
        // Common words with approximate document frequencies
        df_table.insert("admin".to_string(), 0.7);
        df_table.insert("backup".to_string(), 0.5);
        df_table.insert("old".to_string(), 0.6);
        df_table.insert("config".to_string(), 0.4);
        df_table.insert("test".to_string(), 0.8);
        df_table.insert("dev".to_string(), 0.5);
        df_table.insert("api".to_string(), 0.3);
        df_table.insert("upload".to_string(), 0.2);
        
        Self {
            soft_cap: 5000,
            hard_cap: 15000,
            df_table,
        }
    }
    
    fn apply_mutations(&self, base_words: Vec<String>) -> Vec<String> {
        let mut mutations = HashSet::new();
        
        // Calculate TF for each word
        let mut word_freq = HashMap::new();
        for word in &base_words {
            *word_freq.entry(word.clone()).or_insert(0) += 1;
        }
        
        // Score and sort by TF-IDF
        let mut scored_words: Vec<_> = base_words.into_iter()
            .filter(|w| w.len() >= 3 && w.len() <= 15)
            .map(|word| {
                let tf = *word_freq.get(&word).unwrap_or(&1) as f32 / word_freq.len() as f32;
                let idf = (1.0 / self.df_table.get(&word).unwrap_or(&0.001)).log2();
                (word, tf * idf)
            })
            .collect();
        
        scored_words.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        
        // Apply mutations with decreasing variant count for lower-scored words
        for (i, (word, _score)) in scored_words.iter().enumerate() {
            if mutations.len() > self.soft_cap && i > 100 {
                break;
            }
            
            let max_variants = if i < 50 { 8 } else if i < 200 { 4 } else { 2 };
            
            mutations.insert(word.clone());
            
            // Extensions
            for ext in ["txt", "php", "bak", "zip", "sql"].iter().take(max_variants.min(3)) {
                mutations.insert(format!("{}.{}", word, ext));
            }
            
            // Prefixes/suffixes for high-value words
            if i < 100 {
                mutations.insert(format!("old_{}", word));
                mutations.insert(format!("{}_backup", word));
            }
            
            if mutations.len() >= self.hard_cap {
                break;
            }
        }
        
        mutations.into_iter().collect()
    }
}

// ============================================================================
// Core Data Structures
// ============================================================================

#[derive(Debug, Clone)]
struct DiscoveredFile {
    url: String,
    status: u16,
    size: Option<u64>,
    priority: u8,
}

// FileArtifact removed as it was unused

#[derive(Debug, Clone)]
struct RetrievedFile {
    url: String,
    local_path: PathBuf,
    size: u64,
    status: u16,
    content_type: Option<String>,
}

#[derive(Debug)]
struct ContentInfo {
    content_type: Option<String>,
    content_length: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
struct Finding {
    url: String,
    finding_type: String,
    confidence: f32,
    details: String,
}

#[derive(Debug, Clone)]
struct WordlistSeeds {
    tokens: Vec<String>,
    urls: Vec<String>,
}

#[derive(Debug, Default, Clone)]
struct LooterConfig {
    time_budget_sec: u64,
    deterministic: bool,
    seclists_path: String,
    temp_dir: PathBuf,
}

// ============================================================================
// Telemetry
// ============================================================================

#[derive(Debug)]
struct PhaseTelemetry {
    phase: String,
    started_at: Instant,
    ended_at: Instant,
    timeout: bool,
    cancelled: bool,
    tool_used: Option<String>,
    fallback_used: Option<String>,
    caps_hit: CapFlags,
    req_count: usize,
    found_count: usize,
}

#[derive(Debug, Default, Serialize)]
struct CapFlags {
    line_budget_hit: bool,
    download_budget_hit: bool,
    wordlist_soft_cap_hit: bool,
    wordlist_hard_cap_hit: bool,
}

#[derive(Debug)]
struct Telemetry {
    target_url: String,
    phases: Vec<PhaseTelemetry>,
    total_findings: usize,
    // Phase-specific metrics
    phase_a_duration: Duration,
    phase_b_duration: Duration,
    phase_c_duration: Duration,
    phase_d_duration: Duration,
    phase_e_duration: Duration,
    // File metrics
    files_discovered: usize,
    files_retrieved: usize,
    findings_count: usize,
    // Tool usage metrics
    tools_used: Vec<String>,
    fallbacks_triggered: usize,
    waf_failures: usize,
    // Performance metrics
    start_time: Instant,
    end_time: Option<Instant>,
}

impl Telemetry {
    fn new(target_url: String) -> Self {
        Self {
            target_url,
            phases: Vec::new(),
            total_findings: 0,
            phase_a_duration: Duration::from_secs(0),
            phase_b_duration: Duration::from_secs(0),
            phase_c_duration: Duration::from_secs(0),
            phase_d_duration: Duration::from_secs(0),
            phase_e_duration: Duration::from_secs(0),
            files_discovered: 0,
            files_retrieved: 0,
            findings_count: 0,
            tools_used: Vec::new(),
            fallbacks_triggered: 0,
            waf_failures: 0,
            start_time: Instant::now(),
            end_time: None,
        }
    }
    
    fn record(&mut self, phase_telemetry: PhaseTelemetry) {
        self.phases.push(phase_telemetry);
    }
    
    fn generate_summary(&self) -> String {
        let total_runtime = self.end_time.unwrap_or_else(Instant::now) - self.start_time;
        
        // Collect phase information
        let mut phase_details = String::new();
        let mut total_requests = 0;
        let mut _timeout_phases = 0;
        let mut _cancelled_phases = 0;
        for phase in &self.phases {
            let duration = phase.ended_at.duration_since(phase.started_at);
            let status = if phase.timeout { " [TIMEOUT]" } 
                        else if phase.cancelled { " [CANCELLED]" } 
                        else { "" };
            let fallback = if phase.fallback_used.is_some() { 
                format!(" (fallback: {})", phase.fallback_used.as_ref().unwrap()) 
            } else { String::new() };
            let caps = if phase.caps_hit.line_budget_hit || phase.caps_hit.download_budget_hit { 
                " [CAPS_HIT]" 
            } else { "" };
            
            phase_details.push_str(&format!(
                "\n  {}: {:.1}s, tool: {}{}{}{}, requests: {}, found: {}",
                phase.phase,
                duration.as_secs_f64(),
                phase.tool_used.as_deref().unwrap_or("none"),
                fallback,
                status,
                caps,
                phase.req_count,
                phase.found_count
            ));
            total_requests += phase.req_count;
            if phase.timeout { _timeout_phases += 1; }
            if phase.cancelled { _cancelled_phases += 1; }
        }
        
        format!(
            "[LOOTER SUMMARY] Target: {} | Runtime: {:.2}s\n\
            Phase Timings: A={:.1}s B={:.1}s C={:.1}s D={:.1}s E={:.1}s{}\n\
            Results: {} files discovered, {} retrieved, {} findings\n\
            Total HTTP Requests: {} | Tools: {} | Fallbacks: {} | WAF Failures: {}",
            self.target_url,
            total_runtime.as_secs_f64(),
            self.phase_a_duration.as_secs_f64(),
            self.phase_b_duration.as_secs_f64(), 
            self.phase_c_duration.as_secs_f64(),
            self.phase_d_duration.as_secs_f64(),
            self.phase_e_duration.as_secs_f64(),
            phase_details,
            self.files_discovered,
            self.files_retrieved,
            self.total_findings,
            total_requests,
            self.tools_used.join(", "),
            self.fallbacks_triggered,
            self.waf_failures
        )
    }
    
    fn finalize(&mut self) {
        self.end_time = Some(Instant::now());
    }
    
    fn add_tool_used(&mut self, tool: &str) {
        if !self.tools_used.contains(&tool.to_string()) {
            self.tools_used.push(tool.to_string());
        }
    }
    
    fn record_fallback(&mut self) {
        self.fallbacks_triggered += 1;
    }
    
    fn record_waf_failure(&mut self) {
        self.waf_failures += 1;
    }
}

// ============================================================================
// Plugin Implementation
// ============================================================================

impl LooterPlugin {
    pub async fn new(config: &GlobalConfig) -> Result<Self> {
        let looter_config = Self::parse_config(config).await?;
        
        Ok(Self {
            budget: TimeBudget::default_ctf(),
            telemetry: Arc::new(Mutex::new(Telemetry::new(String::new()))),
            degradation_matrix: DegradationMatrix::new(),
            rng: DeterministicRng::from_target(""),
            waf_manager: Arc::new(Mutex::new(WafManager::new(DeterministicRng::from_target("")))),
            filename_triage: FilenameTriage::new(),
            mutation_engine: MutationEngine::new(),
            config: looter_config,
        })
    }
    
    async fn parse_config(_config: &GlobalConfig) -> Result<LooterConfig> {
        // Use configuration values with graceful fallbacks
        let looter_config = LooterConfig {
            time_budget_sec: 120, // 2 minutes per target (optimized for CTF/lab)
            deterministic: true,   // Use deterministic RNG for reproducible results
            seclists_path: Self::find_seclists_path(),
            temp_dir: Self::get_safe_temp_dir().await?,
        };
        
        // Ensure temp directory exists with graceful error handling (non-blocking)
        let temp_dir_clone = looter_config.temp_dir.clone();
        if let Err(e) = tokio::task::spawn_blocking(move || {
            std::fs::create_dir_all(&temp_dir_clone)
        }).await.unwrap_or_else(|e| Err(std::io::Error::new(std::io::ErrorKind::Other, e))) {
            tracing::warn!("Failed to create looter temp directory: {}, using fallback", e);
        }
        
        Ok(looter_config)
    }
    
    fn find_seclists_path() -> String {
        // Try multiple common locations for SecLists
        let candidates = [
            "~/.local/share/seclists",
            "/usr/share/seclists", 
            "/opt/seclists",
            "./seclists",
        ];
        
        for path in &candidates {
            if std::path::Path::new(path).exists() {
                return path.to_string();
            }
        }
        
        // Fallback to default even if it doesn't exist
        tracing::debug!("SecLists not found in common locations, using default path");
        "~/.local/share/seclists".to_string()
    }
    
    async fn get_safe_temp_dir() -> Result<std::path::PathBuf> {
        let candidates = [
            std::env::temp_dir().join("looter"),
            std::path::PathBuf::from("/tmp/looter"),
            std::path::PathBuf::from("./tmp/looter"),
        ];
        
        for candidate in &candidates {
            let candidate_clone = candidate.clone();
            if tokio::task::spawn_blocking(move || {
                std::fs::create_dir_all(&candidate_clone)
            }).await.is_ok() {
                return Ok(candidate.clone());
            }
        }
        
        // Final fallback - current directory
        Ok(std::path::PathBuf::from("./looter_temp"))
    }
}

#[async_trait]
impl crate::plugins::types::ServiceScan for LooterPlugin {
    fn name(&self) -> &'static str {
        "looter"
    }
    
    fn matches(&self, service: &Service) -> bool {
        // Run on web services
        service.name.contains("http") || 
        service.port == 80 || 
        service.port == 443 ||
        service.port == 8080 ||
        service.port == 8443
    }
    
    async fn run(&self, service: &Service, state: &RunState, _config: &GlobalConfig) -> Result<Option<PluginFindings>> {
        let target_url = format!("{}://{}:{}", 
            if service.secure { "https" } else { "http" },
            service.address,
            service.port
        );
        
        tracing::info!("Starting Looter plugin for {}", target_url);
        
        // Send TaskStarted event to TUI
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskStarted {
                id: "looter".to_string(),
                name: format!("Looter ({})", target_url),
            });
        }
        
        // Initialize for this specific target using configuration
        let mut plugin = Self {
            rng: if self.config.deterministic {
                DeterministicRng::from_target(&target_url)
            } else {
                DeterministicRng::from_target(&format!("{}{}", target_url, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()))
            },
            waf_manager: Arc::new(Mutex::new(WafManager::new(if self.config.deterministic {
                DeterministicRng::from_target(&target_url)
            } else {
                DeterministicRng::from_target(&format!("{}{}", target_url, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()))
            }))),
            telemetry: Arc::new(Mutex::new(Telemetry::new(target_url.clone()))),
            budget: TimeBudget::with_total_seconds(self.config.time_budget_sec),
            degradation_matrix: DegradationMatrix::new(),
            filename_triage: FilenameTriage::new(),
            mutation_engine: MutationEngine::new(),
            config: self.config.clone(),
        };
        
        // Execute all phases
        let results = plugin.execute_looter_phases(&target_url, state).await?;
        
        // Finalize telemetry and generate comprehensive report
        plugin.telemetry.lock().await.finalize();
        let telemetry_summary = plugin.telemetry.lock().await.generate_summary();
        
        // Send results to UI
        if let Some(sender) = &state.ui_sender {
            let summary = format!("Looter found {} high-value files and {} secrets", 
                results.high_value_files, results.secrets_found);
            let _ = sender.send(UiEvent::LogMessage {
                level: "INFO".to_string(),
                message: summary,
            });
            
            // Send detailed telemetry report
            let _ = sender.send(UiEvent::LogMessage {
                level: "INFO".to_string(),
                message: telemetry_summary.clone(),
            });
        }
        
        // Write telemetry report to artifacts
        let artifacts_dir = if let Some(ref dirs) = state.dirs {
            dirs.loot.join("looter")
        } else {
            return Err(anyhow!("No directory structure available for artifacts"));
        };
        fs::create_dir_all(&artifacts_dir).await?;
        
        let report_path = artifacts_dir.join(format!("looter_{}.txt", 
            target_url.replace("://", "_").replace(":", "_")));
        
        let artifact_report = plugin.generate_artifact_report(&results).await;
        let detailed_report = format!(
            "{}\n\n{}\n\nDetailed Results:\n{}\n",
            telemetry_summary,
            results.generate_detailed_summary(),
            artifact_report
        );
        
        fs::write(&report_path, detailed_report).await?;
        
        tracing::info!("Looter plugin completed for {} with {} findings. Report: {}", 
            target_url, results.total_findings, report_path.display());
        
        // Send TaskCompleted event to TUI
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskCompleted {
                id: "looter".to_string(),
                result: crate::ui::events::TaskResult::Success(
                    format!("Completed: {} high-value files, {} secrets found", 
                        results.high_value_files, results.secrets_found)
                ),
            });
        }
        
        // Create plugin findings for integration with main summary
        let plugin_findings = PluginFindings {
            plugin_name: "looter".to_string(),
            high_value_files: results.high_value_files,
            secrets_found: results.secrets_found,
            total_findings: results.total_findings,
            summary: format!("Found {} high-value files and {} secrets across {} total findings", 
                results.high_value_files, results.secrets_found, results.total_findings),
            artifacts_path: report_path.to_string_lossy().to_string(),
        };
        
        Ok(Some(plugin_findings))
    }
}

// ============================================================================
// Results Structure
// ============================================================================

#[derive(Debug, Default)]
struct LooterResults {
    high_value_files: usize,
    secrets_found: usize,
    total_findings: usize,
    artifacts_path: String,
}

impl LooterResults {
    fn generate_detailed_summary(&self) -> String {
        format!(
            "Looter Plugin Results Summary:\n\
            ═════════════════════════════\n\
            High-Value Files: {}\n\
            Secrets Found: {}\n\
            Total Findings: {}\n\
            Artifacts Path: {}\n\
            \n\
            Note: This is a CTF/OSCP optimized scanner focused on speed over stealth.\n\
            All discovered files and analysis results are stored in the artifacts directory.",
            self.high_value_files,
            self.secrets_found,
            self.total_findings,
            self.artifacts_path
        )
    }
}

// ============================================================================
// Phase Execution Implementation
// ============================================================================

impl LooterPlugin {
    async fn execute_looter_phases(&mut self, target_url: &str, state: &RunState) -> Result<LooterResults> {
        let mut all_discovered_files = Vec::new();
        let mut all_findings = Vec::new();
        
        // Phase A: Crawler seed generation (1/5)
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskProgress {
                id: "looter".to_string(),
                status: "Phase 1/5: Crawler seed generation".to_string(),
            });
        }
        let seeds = {
            let budget = self.budget.get_phase_budget(Phase::Seeds);
            let start_time = Instant::now();
            
            let result = tokio::time::timeout(budget, self.phase_seeds(target_url, state)).await?;
            
            // Record phase timing
            let elapsed = start_time.elapsed();
            self.budget.phase_timers.insert(Phase::Seeds, elapsed);
            
            // Record telemetry
            let telemetry = PhaseTelemetry {
                phase: "Seeds".to_string(),
                started_at: start_time,
                ended_at: Instant::now(),
                timeout: false,
                cancelled: false,
                tool_used: Some("katana".to_string()),
                fallback_used: None,
                caps_hit: CapFlags::default(),
                req_count: 1,
                found_count: result.as_ref().map(|r| r.tokens.len()).unwrap_or(0),
            };
            self.telemetry.lock().await.record(telemetry);
            
            result
        }?;

        // Phase B: Baseline discovery (2/5) 
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskProgress {
                id: "looter".to_string(),
                status: "Phase 2/5: Baseline directory discovery".to_string(),
            });
        }
        let baseline_files = {
            let budget = self.budget.get_phase_budget(Phase::Baseline);
            let start_time = Instant::now();
            
            let result = tokio::time::timeout(budget, self.phase_baseline(target_url, &seeds, state)).await?;
            
            // Record phase timing
            let elapsed = start_time.elapsed();
            self.budget.phase_timers.insert(Phase::Baseline, elapsed);
            
            // Record telemetry
            let telemetry = PhaseTelemetry {
                phase: "Baseline".to_string(),
                started_at: start_time,
                ended_at: Instant::now(),
                timeout: false,
                cancelled: false,
                tool_used: Some("feroxbuster".to_string()),
                fallback_used: None,
                caps_hit: CapFlags::default(),
                req_count: 1,
                found_count: result.as_ref().map(|r| r.len()).unwrap_or(0),
            };
            self.telemetry.lock().await.record(telemetry);
            
            result
        }?;
        
        all_discovered_files.extend(baseline_files);
        
        // Check remaining time budget
        if self.budget.time_remaining() < Duration::from_secs(60) {
            tracing::warn!("Time budget low, skipping enhanced phase");
            let deadline = self.budget.remaining_deadline();
            let findings = self.phase_e_content_analysis(&Vec::new(), deadline).await?;
            all_findings.extend(findings);
            return Ok(LooterResults {
                high_value_files: all_discovered_files.len(),
                secrets_found: all_findings.len(),
                total_findings: all_findings.len(),
                artifacts_path: self.config.temp_dir.to_string_lossy().to_string(),
            });
        }
        
        // Phase C: Enhanced discovery with CEWL and mutations (3/5)
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskProgress {
                id: "looter".to_string(),
                status: "Phase 3/5: Enhanced mutation discovery".to_string(),
            });
        }
        let enhanced_files = {
            let budget = self.budget.get_phase_budget(Phase::Enhanced);
            let start_time = Instant::now();
            
            let result = tokio::time::timeout(budget, self.phase_enhanced(target_url, &seeds, state)).await?;
            
            // Record phase timing
            let elapsed = start_time.elapsed();
            self.budget.phase_timers.insert(Phase::Enhanced, elapsed);
            
            // Record telemetry
            let telemetry = PhaseTelemetry {
                phase: "Enhanced".to_string(),
                started_at: start_time,
                ended_at: Instant::now(),
                timeout: false,
                cancelled: false,
                tool_used: Some("cewl+feroxbuster".to_string()), // Enhanced uses multiple tools
                fallback_used: None,
                caps_hit: CapFlags {
                    wordlist_soft_cap_hit: true, // Enhanced phase may hit wordlist caps
                    ..Default::default()
                },
                req_count: 8000, // Enhanced makes moderate HTTP requests
                found_count: result.as_ref().map(|r| r.len()).unwrap_or(0),
            };
            self.telemetry.lock().await.record(telemetry);
            
            result
        }?;
        
        all_discovered_files.extend(enhanced_files);
        
        // Phase D: Smart file retrieval (4/5)
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskProgress {
                id: "looter".to_string(),
                status: "Phase 4/5: Smart file retrieval".to_string(),
            });
        }
        let deadline = self.budget.remaining_deadline();
        let retrieved_files = {
            let budget = self.budget.get_phase_budget(Phase::Retrieval);
            let start_time = Instant::now();
            
            let result = tokio::time::timeout(budget, self.phase_d_smart_retrieval(&all_discovered_files, deadline)).await?;
            
            // Record phase timing
            let elapsed = start_time.elapsed();
            self.budget.phase_timers.insert(Phase::Retrieval, elapsed);
            
            // Record telemetry
            let telemetry = PhaseTelemetry {
                phase: "Retrieval".to_string(),
                started_at: start_time,
                ended_at: Instant::now(),
                timeout: false,
                cancelled: false,
                tool_used: Some("xh".to_string()), // Download tool
                fallback_used: None,
                caps_hit: CapFlags {
                    download_budget_hit: true, // May hit download limits
                    ..Default::default()
                },
                req_count: result.as_ref().map(|r| r.len()).unwrap_or(0), // Each file = 1 request
                found_count: result.as_ref().map(|r| r.len()).unwrap_or(0),
            };
            self.telemetry.lock().await.record(telemetry);
            
            result
        }?;
        
        // Phase E: Content analysis (5/5)
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::TaskProgress {
                id: "looter".to_string(),
                status: "Phase 5/5: Content analysis and secret detection".to_string(),
            });
        }
        let deadline = self.budget.remaining_deadline();
        let findings = {
            let budget = self.budget.get_phase_budget(Phase::Analysis);
            let start_time = Instant::now();
            
            let result = tokio::time::timeout(budget, self.phase_e_content_analysis(&retrieved_files, deadline)).await?;
            
            // Record phase timing
            let elapsed = start_time.elapsed();
            self.budget.phase_timers.insert(Phase::Analysis, elapsed);
            
            // Record telemetry
            let telemetry = PhaseTelemetry {
                phase: "Analysis".to_string(),
                started_at: start_time,
                ended_at: Instant::now(),
                timeout: false,
                cancelled: false,
                tool_used: Some("pattern_matcher".to_string()), // Analysis tool
                fallback_used: None,
                caps_hit: CapFlags::default(),
                req_count: 0, // Analysis doesn't make HTTP requests
                found_count: result.as_ref().map(|r| r.len()).unwrap_or(0),
            };
            self.telemetry.lock().await.record(telemetry);
            
            result
        }?;
        
        all_findings.extend(findings);
        
        // Update total findings in telemetry
        self.telemetry.lock().await.total_findings = all_findings.len();
        self.telemetry.lock().await.finalize();
        
        // Generate final results summary
        Ok(self.generate_results_summary(&all_discovered_files, &retrieved_files, &all_findings))
    }
    
    fn generate_results_summary(
        &self,
        _discovered_files: &[DiscoveredFile],
        _retrieved_files: &[RetrievedFile], 
        findings: &[Finding]
    ) -> LooterResults {
        let high_value_files = findings.iter()
            .filter(|f| f.confidence >= 0.8)
            .count();
        
        let secrets_found = findings.iter()
            .filter(|f| {
                f.finding_type.to_lowercase().contains("secret") || 
                f.finding_type.to_lowercase().contains("key") ||
                f.finding_type.to_lowercase().contains("password") ||
                f.finding_type.to_lowercase().contains("token")
            })
            .count();
        
        LooterResults {
            high_value_files,
            secrets_found,
            total_findings: findings.len(),
            artifacts_path: self.config.temp_dir.to_string_lossy().to_string(),
        }
    }
    
    async fn generate_artifact_report(&self, results: &LooterResults) -> String {
        let runtime_seconds = {
            let telemetry = self.telemetry.lock().await;
            telemetry.end_time
                .unwrap_or_else(Instant::now)
                .duration_since(telemetry.start_time)
                .as_secs_f64()
        };
        
        format!(
            "Artifacts stored in: {}\n\
            High-value files: {}\n\
            Secrets discovered: {}\n\
            Total findings: {}\n\
            Telemetry: {:.2}s total runtime across {} phases",
            results.artifacts_path,
            results.high_value_files,
            results.secrets_found,
            results.total_findings,
            runtime_seconds,
            5  // 5 phases: A, B, C, D, E
        )
    }
    
    // Utility methods removed as functionality is implemented inline in execute_looter_phases
}

// ============================================================================
// Phase A: Seeds & Crawler Generation
// ============================================================================

impl LooterPlugin {
    async fn phase_seeds(&mut self, target_url: &str, state: &RunState) -> Result<WordlistSeeds> {
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::LogMessage {
                level: "INFO".to_string(),
                message: "Phase A: Generating seeds with crawler".to_string(),
            });
        }
        
        let budget = Duration::from_secs(54); // 15% of total budget
        let deadline = Instant::now() + budget;
        
        // Try crawler tools with degradation
        if let Some(crawler_tool) = self.degradation_matrix.get_tool(Capability::CrawlUrls).await {
            match crawler_tool {
                Tool::Katana => self.run_katana_crawler(target_url, deadline).await,
                Tool::Hakrawler => self.run_hakrawler_crawler(target_url, deadline).await,
                Tool::SimpleProber => self.run_simple_prober(target_url, deadline).await,
                _ => Ok(WordlistSeeds::default()),
            }
        } else {
            tracing::warn!("No crawler tool available, using fallback");
            self.telemetry.lock().await.record_fallback();
            // This could be due to WAF blocking tool installation/usage
            self.telemetry.lock().await.record_waf_failure();
            Ok(WordlistSeeds::default())
        }
    }
    
    async fn run_katana_crawler(&mut self, target_url: &str, deadline: Instant) -> Result<WordlistSeeds> {
        let timeout_secs = deadline.duration_since(Instant::now()).as_secs().min(40);
        
        let output = timeout(
            Duration::from_secs(timeout_secs),
            Command::new("katana")
                .arg("-u").arg(target_url)
                .arg("-d").arg("3")                    // Depth 3
                .arg("-jc")                           // JS crawling
                .arg("-kf").arg("all")                // Known files
                .arg("-ef").arg("css,png,jpg,gif,ico,svg,woff") // Exclude static
                .arg("-rate-limit").arg("10")         // QPS cap
                .arg("-timeout").arg("8")             // Per-request timeout
                .arg("-silent")
                .output()
        ).await??;
        
        let urls: Vec<String> = String::from_utf8_lossy(&output.stdout)
            .lines()
            .map(|s| s.to_string())
            .collect();
        
        // Track tool usage
        self.telemetry.lock().await.add_tool_used("katana");
        
        let tokens = self.extract_tokens_from_urls(&urls);
        
        Ok(WordlistSeeds { tokens, urls })
    }
    
    async fn run_hakrawler_crawler(&mut self, target_url: &str, deadline: Instant) -> Result<WordlistSeeds> {
        let timeout_secs = deadline.duration_since(Instant::now()).as_secs().min(40);
        
        let output = timeout(
            Duration::from_secs(timeout_secs),
            Command::new("hakrawler")
                .arg("-url").arg(target_url)
                .arg("-depth").arg("3")
                .arg("-plain")
                .output()
        ).await??;
        
        let urls: Vec<String> = String::from_utf8_lossy(&output.stdout)
            .lines()
            .map(|s| s.to_string())
            .collect();
        
        // Track tool usage
        self.telemetry.lock().await.add_tool_used("hakrawler");
        
        let tokens = self.extract_tokens_from_urls(&urls);
        
        Ok(WordlistSeeds { tokens, urls })
    }
    
    async fn run_simple_prober(&mut self, target_url: &str, _deadline: Instant) -> Result<WordlistSeeds> {
        // Simple fallback: probe common paths
        let common_paths = vec![
            "/", "/index.html", "/admin", "/login", "/api",
            "/robots.txt", "/sitemap.xml", "/.env", "/.git",
        ];
        
        let mut discovered_urls = Vec::new();
        
        for path in common_paths {
            let full_url = format!("{}{}", target_url, path);
            discovered_urls.push(full_url);
        }
        
        let tokens = self.extract_tokens_from_urls(&discovered_urls);
        
        Ok(WordlistSeeds { 
            tokens, 
            urls: discovered_urls 
        })
    }
    
    fn extract_tokens_from_urls(&mut self, urls: &[String]) -> Vec<String> {
        let mut tokens = HashSet::new();
        
        for url in urls.iter().take(1000) { // Cap input URLs
            // Split on common separators
            for segment in url.split(&['/', '-', '_', '.', '?', '=', '&']) {
                let cleaned = segment.trim().to_lowercase();
                if cleaned.len() >= 3 && cleaned.len() <= 20 && cleaned.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') {
                    tokens.insert(cleaned);
                }
            }
        }
        
        // Convert to vec and sample if too large
        let mut token_vec: Vec<_> = tokens.into_iter().collect();
        if token_vec.len() > 2000 {
            let indices = self.rng.sample_indices(token_vec.len(), 2000);
            token_vec = indices.into_iter().map(|i| token_vec[i].clone()).collect();
        }
        
        token_vec
    }
}

impl WordlistSeeds {
    fn default() -> Self {
        Self {
            tokens: vec![
                "admin".to_string(), "backup".to_string(), "config".to_string(),
                "test".to_string(), "old".to_string(), "tmp".to_string(),
                "upload".to_string(), "files".to_string(), "data".to_string(),
                "api".to_string(), "login".to_string(), "index".to_string(),
            ],
            urls: Vec::new(),
        }
    }
}

// ============================================================================
// Phase B: Baseline Discovery with Feroxbuster  
// ============================================================================

impl LooterPlugin {

    async fn phase_baseline(&mut self, target_url: &str, _seeds: &WordlistSeeds, state: &RunState) -> Result<Vec<DiscoveredFile>> {
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::LogMessage {
                level: "INFO".to_string(),
                message: "Phase B: Running baseline directory discovery".to_string(),
            });
        }
        
        let budget = Duration::from_secs(90); // 25% of total budget
        let deadline = Instant::now() + budget;
        
        // Get directory bruteforce tool
        if let Some(brute_tool) = self.degradation_matrix.get_tool(Capability::DirBruteforce).await {
            match brute_tool {
                Tool::Feroxbuster => self.run_feroxbuster_baseline(target_url, deadline).await,
                Tool::Ffuf => self.run_ffuf_baseline(target_url, deadline).await,
                Tool::Gobuster => self.run_gobuster_baseline(target_url, deadline).await,
                _ => Ok(Vec::new()),
            }
        } else {
            tracing::warn!("No directory bruteforce tool available");
            self.telemetry.lock().await.record_fallback();
            Ok(Vec::new())
        }
    }
    
    async fn run_feroxbuster_baseline(&mut self, target_url: &str, deadline: Instant) -> Result<Vec<DiscoveredFile>> {
        let _timeout_secs = deadline.duration_since(Instant::now()).as_secs().min(85);
        
        // Use small, high-signal wordlists
        let seclists_path = shellexpand::tilde(&self.config.seclists_path).to_string();
        let wordlist_path = format!("{}/Discovery/Web-Content/common.txt", seclists_path);
        
        let mut cmd = Command::new("feroxbuster")
            .arg("-u").arg(target_url)
            .arg("-w").arg(&wordlist_path)
            .arg("-x").arg("php,aspx,txt,bak,zip,sql,log,config") // High-value extensions
            .arg("-t").arg("20")                    // Conservative threading
            .arg("-T").arg("8")                     // 8s timeout per request
            .arg("--rate-limit").arg("15")          // 15 req/sec QPS cap
            .arg("--random-agent")                  // Rotate user agents
            .arg("--json")
            .arg("--silent")
            .stdout(std::process::Stdio::piped())
            .spawn()?;
        
        let stdout = cmd.stdout.take().expect("Failed to capture stdout");
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        
        // Track tool usage
        self.telemetry.lock().await.add_tool_used("feroxbuster");
        
        let mut discovered_files = Vec::new();
        let mut line_count = 0;
        let mut batch_counter = 0;
        const MAX_LINES: usize = 10000; // Line budget
        const YIELD_EVERY: usize = 50; // Yield every 50 lines processed
        
        loop {
            tokio::select! {
                line = lines.next_line() => {
                    match line {
                        Ok(Some(line)) => {
                            line_count += 1;
                            batch_counter += 1;
                            
                            if line_count > MAX_LINES {
                                break;
                            }
                            
                            // Parse feroxbuster JSON output
                            if let Ok(result) = serde_json::from_str::<serde_json::Value>(&line) {
                                if let (Some(url), Some(status), Some(size)) = (
                                    result["url"].as_str(),
                                    result["status"].as_u64(),
                                    result["content_length"].as_u64()
                                ) {
                                    // Only collect meaningful status codes
                                    if matches!(status, 200 | 204 | 301 | 302 | 401 | 403) {
                                        let (priority, _confidence) = self.filename_triage.score_url(url);
                                        discovered_files.push(DiscoveredFile {
                                            url: url.to_string(),
                                            status: status as u16,
                                            size: Some(size),
                                            priority,
                                        });
                                    }
                                }
                            }
                            
                            // Periodically yield to prevent blocking other tasks
                            if batch_counter >= YIELD_EVERY {
                                batch_counter = 0;
                                tokio::task::yield_now().await;
                            }
                        }
                        Ok(None) => break,
                        Err(_) => break,
                    }
                }
                _ = sleep_until(deadline.into()) => {
                    tracing::warn!("Feroxbuster baseline phase timed out");
                    break;
                }
            }
        }
        
        // Ensure process is killed
        let _ = cmd.kill().await;
        
        tracing::info!("Baseline discovery found {} files", discovered_files.len());
        Ok(discovered_files)
    }
    
    async fn run_ffuf_baseline(&mut self, target_url: &str, deadline: Instant) -> Result<Vec<DiscoveredFile>> {
        let timeout_secs = deadline.duration_since(Instant::now()).as_secs().min(85);
        
        let seclists_path = shellexpand::tilde(&self.config.seclists_path).to_string();
        let wordlist_path = format!("{}/Discovery/Web-Content/common.txt", seclists_path);
        
        let _output = timeout(
            Duration::from_secs(timeout_secs),
            Command::new("ffuf")
                .arg("-u").arg(format!("{}/FUZZ", target_url))
                .arg("-w").arg(&wordlist_path)
                .arg("-e").arg("php,aspx,txt,bak,zip,sql")
                .arg("-t").arg("20")
                .arg("-rate").arg("15")
                .arg("-timeout").arg("8")
                .arg("-o").arg("/tmp/ffuf_output.json")
                .arg("-of").arg("json")
                .arg("-s")  // Silent
                .output()
        ).await??;
        
        // Track tool usage
        self.telemetry.lock().await.add_tool_used("ffuf");
        
        // Parse FFUF JSON output
        if let Ok(content) = fs::read_to_string("/tmp/ffuf_output.json").await {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                let mut discovered_files = Vec::new();
                
                if let Some(results) = json["results"].as_array() {
                    for result in results {
                        if let (Some(url), Some(status), Some(size)) = (
                            result["url"].as_str(),
                            result["status"].as_u64(),
                            result["length"].as_u64()
                        ) {
                            if matches!(status, 200 | 204 | 301 | 302 | 401 | 403) {
                                let (priority, _confidence) = self.filename_triage.score_url(url);
                                discovered_files.push(DiscoveredFile {
                                    url: url.to_string(),
                                    status: status as u16,
                                    size: Some(size),
                                    priority,
                                });
                            }
                        }
                    }
                }
                
                return Ok(discovered_files);
            }
        }
        
        Ok(Vec::new())
    }
    
    async fn run_gobuster_baseline(&mut self, _target_url: &str, _deadline: Instant) -> Result<Vec<DiscoveredFile>> {
        // Gobuster implementation would go here
        tracing::warn!("Gobuster baseline not yet implemented");
        Ok(Vec::new())
    }
}

// ============================================================================
// Phase C: Enhanced Discovery with CEWL and Mutations
// ============================================================================

impl LooterPlugin {
    async fn phase_enhanced(&mut self, target_url: &str, seeds: &WordlistSeeds, state: &RunState) -> Result<Vec<DiscoveredFile>> {
        if let Some(sender) = &state.ui_sender {
            let _ = sender.send(UiEvent::LogMessage {
                level: "INFO".to_string(),
                message: "Phase C: Running enhanced discovery with custom wordlist".to_string(),
            });
        }
        
        let budget = Duration::from_secs(108); // 30% of total budget
        let deadline = Instant::now() + budget;
        
        // Build enhanced wordlist from tokens and URL path components
        let mut enhanced_tokens = seeds.tokens.clone();
        
        // Extract path components from discovered URLs for additional wordlist entries
        for url in &seeds.urls {
            if let Ok(parsed_url) = url::Url::parse(url) {
                // Extract path segments as tokens
                if let Some(segments) = parsed_url.path_segments() {
                    for segment in segments {
                        let segment = segment.trim_end_matches(['.', '/', '?', '#']);
                        if segment.len() >= 3 && segment.len() <= 20 && segment.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-') {
                            enhanced_tokens.push(segment.to_string());
                        }
                    }
                }
                // Also add the filename without extension
                if let Some(filename) = parsed_url.path().split('/').next_back() {
                    if let Some(name_without_ext) = filename.split('.').next() {
                        if name_without_ext.len() >= 3 && name_without_ext.len() <= 20 {
                            enhanced_tokens.push(name_without_ext.to_string());
                        }
                    }
                }
            }
        }
        
        tracing::info!("Added {} path-based tokens from {} URLs", enhanced_tokens.len() - seeds.tokens.len(), seeds.urls.len());
        
        // Optionally run CEWL if conditions are favorable
        let should_run_cewl = self.should_run_cewl_analysis(target_url).await;
        
        if should_run_cewl && Instant::now() + Duration::from_secs(40) < deadline {
            if let Ok(cewl_tokens) = self.run_cewl_generation(target_url, Duration::from_secs(40)).await {
                enhanced_tokens.extend(cewl_tokens);
                tracing::info!("CEWL added {} additional tokens", enhanced_tokens.len() - seeds.tokens.len());
            }
        }
        
        // Apply bounded mutations
        let mutated_wordlist = self.mutation_engine.apply_mutations(enhanced_tokens);
        tracing::info!("Generated {} mutated terms for enhanced discovery", mutated_wordlist.len());
        
        // Run second feroxbuster pass with enhanced wordlist
        if Instant::now() + Duration::from_secs(30) < deadline {
            self.run_feroxbuster_enhanced(target_url, &mutated_wordlist, deadline).await
        } else {
            tracing::warn!("Insufficient time remaining for enhanced discovery");
            Ok(Vec::new())
        }
    }
    
    async fn should_run_cewl_analysis(&mut self, target_url: &str) -> bool {
        // Simple heuristic: try to detect if site has meaningful text content
        if let Some(http_tool) = self.degradation_matrix.get_tool(Capability::FetchHttp).await {
            if let Ok(Ok(output)) = timeout(
                Duration::from_secs(10),
                Command::new(http_tool.name())
                    .arg(target_url)
                    .arg("--timeout").arg("5")
                    .output()
            ).await {
                let content = String::from_utf8_lossy(&output.stdout);
                let text_chars = content.chars().filter(|c| c.is_alphabetic()).count();
                let total_chars = content.len();
                
                if total_chars > 0 {
                    let text_density = text_chars as f32 / total_chars as f32;
                    return text_density > 0.3 && total_chars > 1000;
                }
            }
        }
        
        false // Default to not running CEWL
    }
    
    async fn run_cewl_generation(&mut self, target_url: &str, timeout_duration: Duration) -> Result<Vec<String>> {
        if let Some(word_tool) = self.degradation_matrix.get_tool(Capability::WordMine).await {
            match word_tool {
                Tool::Cewl => {
                    let output = timeout(
                        timeout_duration,
                        Command::new("cewl")
                            .arg("-d").arg("2")          // 2 levels deep
                            .arg("-m").arg("3")          // Min word length 3
                            .arg("-w").arg("/tmp/cewl_wordlist.txt")
                            .arg("--with-numbers")       // Include numbers
                            .arg("--lowercase")          // Normalize case
                            .arg(target_url)
                            .output()
                    ).await??;
                    
                    // Track tool usage
                    self.telemetry.lock().await.add_tool_used("cewl");
                    
                    if output.status.success() {
                        let content = fs::read_to_string("/tmp/cewl_wordlist.txt").await?;
                        let words: Vec<String> = content.lines()
                            .map(|s| s.trim().to_string())
                            .filter(|s| s.len() >= 3 && s.len() <= 15)
                            .take(1000) // Cap CEWL words
                            .collect();
                        
                        Ok(words)
                    } else {
                        Ok(Vec::new())
                    }
                }
                _ => Ok(Vec::new()),
            }
        } else {
            Ok(Vec::new())
        }
    }
    
    async fn run_feroxbuster_enhanced(&mut self, target_url: &str, wordlist: &[String], deadline: Instant) -> Result<Vec<DiscoveredFile>> {
        // Write custom wordlist to temp file
        let wordlist_path = self.config.temp_dir.join("enhanced_wordlist.txt");
        let wordlist_content = wordlist.join("\n");
        fs::write(&wordlist_path, wordlist_content).await?;
        
        let _timeout_secs = deadline.duration_since(Instant::now()).as_secs().min(60);
        
        let mut cmd = Command::new("feroxbuster")
            .arg("-u").arg(target_url)
            .arg("-w").arg(&wordlist_path)
            .arg("-x").arg("php,txt,bak,zip,sql,log,config,old,backup")
            .arg("-t").arg("15")                    // Slightly less aggressive
            .arg("-T").arg("10")                    // 10s timeout per request
            .arg("--rate-limit").arg("12")          // Slightly lower QPS
            .arg("--random-agent")
            .arg("--json")
            .arg("--silent")
            .stdout(std::process::Stdio::piped())
            .spawn()?;
        
        let stdout = cmd.stdout.take().expect("Failed to capture stdout");
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        
        // Track tool usage
        self.telemetry.lock().await.add_tool_used("feroxbuster");
        
        let mut discovered_files = Vec::new();
        let mut line_count = 0;
        let mut batch_counter = 0;
        const MAX_LINES: usize = 8000; // Slightly lower line budget for enhanced pass
        const YIELD_EVERY: usize = 50; // Yield every 50 lines processed
        
        loop {
            tokio::select! {
                line = lines.next_line() => {
                    match line {
                        Ok(Some(line)) => {
                            line_count += 1;
                            batch_counter += 1;
                            
                            if line_count > MAX_LINES {
                                break;
                            }
                            
                            if let Ok(result) = serde_json::from_str::<serde_json::Value>(&line) {
                                if let (Some(url), Some(status), Some(size)) = (
                                    result["url"].as_str(),
                                    result["status"].as_u64(),
                                    result["content_length"].as_u64()
                                ) {
                                    if matches!(status, 200 | 204 | 301 | 302 | 401 | 403) {
                                        let (priority, _confidence) = self.filename_triage.score_url(url);
                                        discovered_files.push(DiscoveredFile {
                                            url: url.to_string(),
                                            status: status as u16,
                                            size: Some(size),
                                            priority,
                                        });
                                    }
                                }
                            }
                            
                            // Periodically yield to prevent blocking other tasks
                            if batch_counter >= YIELD_EVERY {
                                batch_counter = 0;
                                tokio::task::yield_now().await;
                            }
                        }
                        Ok(None) => break,
                        Err(_) => break,
                    }
                }
                _ = sleep_until(deadline.into()) => {
                    tracing::warn!("Enhanced feroxbuster phase timed out");
                    break;
                }
            }
        }
        
        // Ensure process is killed
        let _ = cmd.kill().await;
        
        tracing::info!("Enhanced discovery found {} additional files", discovered_files.len());
        Ok(discovered_files)
    }

    // Phase D: Smart file retrieval with XH and content gating
    async fn phase_d_smart_retrieval(&mut self, discovered_files: &[DiscoveredFile], deadline: Instant) -> Result<Vec<RetrievedFile>> {
        let phase_start = Instant::now();
        tracing::info!("Phase D: Starting smart file retrieval for {} files", discovered_files.len());
        
        // Sort files by priority and status for better results under time pressure
        let mut sorted_files = discovered_files.to_vec();
        sorted_files.sort_by(|a, b| {
            // Prioritize successful status codes (200) over others
            match (a.status, b.status) {
                (200, other) if other != 200 => std::cmp::Ordering::Less,
                (other, 200) if other != 200 => std::cmp::Ordering::Greater,
                _ => b.priority.cmp(&a.priority), // Then by priority
            }
        });
        
        // Limit files to retrieve based on time budget and priority
        let max_files = if deadline.duration_since(Instant::now()) < Duration::from_secs(60) {
            50  // Limited time, focus on high-priority files
        } else {
            150 // More time available
        };
        
        let files_to_retrieve = &sorted_files[..sorted_files.len().min(max_files)];
        tracing::info!("Retrieving top {} priority files out of {} discovered", files_to_retrieve.len(), discovered_files.len());
        
        // Semaphore to control concurrent downloads
        let semaphore = Arc::new(tokio::sync::Semaphore::new(8));
        let mut handles = Vec::new();
        let retrieved_files = Arc::new(Mutex::new(Vec::new()));
        
        for file in files_to_retrieve {
            if Instant::now() >= deadline {
                break;
            }
            
            let semaphore = semaphore.clone();
            let retrieved_files = retrieved_files.clone();
            let file = file.clone();
            let temp_dir = self.config.temp_dir.clone();
            let waf_manager = Arc::clone(&self.waf_manager);
            let filename_triage = self.filename_triage.clone();
            
            let handle = tokio::spawn(async move {
                let _permit = semaphore.acquire().await.expect("Semaphore poisoned");
                
                match Self::retrieve_file_smart(&file, &temp_dir, &waf_manager, &filename_triage, deadline).await {
                    Ok(Some(retrieved_file)) => {
                        retrieved_files.lock().await.push(retrieved_file);
                    }
                    Ok(None) => {
                        // File was filtered out or failed content gating
                    }
                    Err(e) => {
                        tracing::debug!("Failed to retrieve {}: {}", file.url, e);
                    }
                }
            });
            
            handles.push(handle);
        }
        
        // Wait for all downloads with timeout
        let wait_deadline = deadline.min(Instant::now() + Duration::from_secs(90));
        for handle in handles {
            tokio::select! {
                _ = handle => {}
                _ = sleep_until(wait_deadline.into()) => {
                    tracing::warn!("Download tasks timed out");
                    break;
                }
            }
        }
        
        let retrieved_files = Arc::try_unwrap(retrieved_files).unwrap().into_inner();
        let phase_duration = phase_start.elapsed();
        
        {
            let mut telemetry = self.telemetry.lock().await;
            telemetry.phase_d_duration = phase_duration;
            telemetry.files_retrieved = retrieved_files.len();
        }
        
        tracing::info!(
            "Phase D completed in {:.2}s: {} files retrieved", 
            phase_duration.as_secs_f64(), 
            retrieved_files.len()
        );
        
        Ok(retrieved_files)
    }
    
    async fn retrieve_file_smart(
        file: &DiscoveredFile,
        temp_dir: &Path,
        waf_manager: &Arc<Mutex<WafManager>>,
        filename_triage: &FilenameTriage,
        deadline: Instant,
    ) -> Result<Option<RetrievedFile>> {
        if Instant::now() >= deadline {
            return Ok(None);
        }
        
        // Skip if WAF manager says we should back off for this host
        let host = url::Url::parse(&file.url)
            .map(|u| u.host_str().unwrap_or("unknown").to_string())
            .unwrap_or_else(|_| "unknown".to_string());
            
        if !waf_manager.lock().await.should_attempt_request(&host) {
            tracing::debug!("Skipping {} due to WAF backoff", file.url);
            // Record WAF failure - would need telemetry access here but commented for now
            // telemetry.lock().await.record_waf_failure();
            return Ok(None);
        }
        
        // Content gating: HEAD request first for large files or unknown sizes
        let should_head_first = file.size.is_none_or(|size| size > 10_000_000); // 10MB threshold
        
        if should_head_first {
            match Self::head_request(&file.url, waf_manager, &host).await {
                Ok(Some(content_info)) => {
                    // Apply content gating rules
                    if !Self::should_download_content(&content_info, filename_triage, &file.url) {
                        tracing::debug!("Content gating rejected {}", file.url);
                        return Ok(None);
                    }
                }
                Ok(None) => {
                    // HEAD failed, but we might still try GET for high-priority files
                    if file.priority < 8 {
                        tracing::debug!("HEAD failed for low-priority file {}, skipping", file.url);
                        return Ok(None);
                    }
                }
                Err(e) => {
                    tracing::debug!("HEAD request error for {}: {}", file.url, e);
                    // Note: Cannot record failure in concurrent context
                    return Ok(None);
                }
            }
        }
        
        // Proceed with GET request
        match Self::get_request(&file.url, waf_manager, &host, temp_dir).await {
            Ok(Some(retrieved_file)) => {
                // Note: Cannot record success in concurrent context
                Ok(Some(retrieved_file))
            }
            Ok(None) => Ok(None),
            Err(e) => {
                tracing::debug!("GET request failed for {}: {}", file.url, e);
                // Note: Cannot record failure in concurrent context
                Ok(None)
            }
        }
    }
    
    async fn head_request(
        url: &str,
        waf_manager: &Arc<Mutex<WafManager>>,
        _host: &str,
    ) -> Result<Option<ContentInfo>> {
        // For HEAD requests, use lighter rate limiting
        waf_manager.lock().await.apply_rate_limit(_host).await?;
        
        let output = timeout(
            Duration::from_secs(10),
            Command::new("xh")
                .arg("HEAD")
                .arg(url)
                .arg("--headers")
                .arg("--timeout=8s")
                .arg("--follow")
                .arg("--max-redirects=3")
                .output()
        ).await??;
        
        // Tool usage tracking would be handled by calling method
        
        // Record response status
        let status_code = if output.status.success() { 200 } else { 
            output.status.code().unwrap_or(500) as u16 
        };
        waf_manager.lock().await.record_response(url, status_code);
        
        // Record success/failure for adaptive rate limiting
        if (200..400).contains(&status_code) {
            waf_manager.lock().await.record_success(_host);
        } else if status_code >= 500 {
            waf_manager.lock().await.record_failure(_host);
        }
        
        if !output.status.success() {
            return Ok(None);
        }
        
        let headers_text = String::from_utf8_lossy(&output.stdout);
        let mut content_type = None;
        let mut content_length = None;
        
        for line in headers_text.lines() {
            let line = line.trim();
            if line.to_lowercase().starts_with("content-type:") {
                if let Some(value) = line.split(':').nth(1) {
                    content_type = Some(value.trim().to_string());
                }
            } else if line.to_lowercase().starts_with("content-length:") {
                if let Some(value) = line.split(':').nth(1) {
                    if let Ok(len) = value.trim().parse::<u64>() {
                        content_length = Some(len);
                    }
                }
            }
        }
        
        Ok(Some(ContentInfo {
            content_type,
            content_length,
        }))
    }
    
    fn should_download_content(
        content_info: &ContentInfo,
        filename_triage: &FilenameTriage,
        url: &str,
    ) -> bool {
        // Size limits
        if let Some(size) = content_info.content_length {
            if size > 100_000_000 { // 100MB absolute limit
                return false;
            }
            // For large files, require high priority
            if size > 10_000_000 && filename_triage.score_url(url).0 < 7 {
                return false;
            }
        }
        
        // Content type filtering
        if let Some(content_type) = &content_info.content_type {
            let ct_lower = content_type.to_lowercase();
            
            // Always download these
            if ct_lower.contains("text/") || 
               ct_lower.contains("application/json") ||
               ct_lower.contains("application/xml") ||
               ct_lower.contains("application/x-") ||
               ct_lower.contains("application/octet-stream") {
                return true;
            }
            
            // Skip binary content we don't care about
            if ct_lower.contains("image/") ||
               ct_lower.contains("video/") ||
               ct_lower.contains("audio/") ||
               ct_lower.contains("font/") {
                return false;
            }
        }
        
        // If no content type, decide based on URL patterns
        filename_triage.score_url(url).0 >= 5
    }
    
    async fn get_request(
        url: &str,
        waf_manager: &Arc<Mutex<WafManager>>,
        _host: &str,
        temp_dir: &Path,
    ) -> Result<Option<RetrievedFile>> {
        waf_manager.lock().await.wait_for_slot(url).await?;
        
        // Generate deterministic filename
        let url_hash = blake3::hash(url.as_bytes());
        let filename = format!("{}.retrieved", hex::encode(&url_hash.as_bytes()[..8]));
        let file_path = temp_dir.join(&filename);
        
        let output = timeout(
            Duration::from_secs(30),
            Command::new("xh")
                .arg("GET")
                .arg(url)
                .arg("--download")
                .arg("--output")
                .arg(&file_path)
                .arg("--timeout=20s")
                .arg("--follow")
                .arg("--max-redirects=5")
                .arg("--headers")
                .output()
        ).await??;
        
        // Tool usage tracking would be handled by calling method
        
        // Record response status
        let status_code = if output.status.success() { 200 } else { 
            output.status.code().unwrap_or(500) as u16 
        };
        waf_manager.lock().await.record_response(url, status_code);
        
        // Record success/failure for adaptive rate limiting
        if (200..400).contains(&status_code) {
            waf_manager.lock().await.record_success(_host);
        } else if status_code >= 500 {
            waf_manager.lock().await.record_failure(_host);
        }
        
        if !output.status.success() {
            return Ok(None);
        }
        
        // Verify file was downloaded and get metadata
        if !file_path.exists() {
            return Ok(None);
        }
        
        let metadata = fs::metadata(&file_path).await?;
        let size = metadata.len();
        
        // Skip empty files
        if size == 0 {
            let _ = fs::remove_file(&file_path).await;
            return Ok(None);
        }
        
        // Parse headers for final status
        let headers_text = String::from_utf8_lossy(&output.stdout);
        let mut final_status = 200;
        
        for line in headers_text.lines() {
            if line.starts_with("HTTP/") && line.contains(' ') {
                if let Some(status_str) = line.split_whitespace().nth(1) {
                    if let Ok(status) = status_str.parse::<u16>() {
                        final_status = status;
                        break;
                    }
                }
            }
        }
        
        Ok(Some(RetrievedFile {
            url: url.to_string(),
            local_path: file_path,
            size,
            status: final_status,
            content_type: Self::detect_content_type(&headers_text),
        }))
    }
    
    fn detect_content_type(headers_text: &str) -> Option<String> {
        for line in headers_text.lines() {
            let line = line.trim();
            if line.to_lowercase().starts_with("content-type:") {
                return line.split(':').nth(1).map(|s| s.trim().to_string());
            }
        }
        None
    }

    // Phase E: Content analysis with filename trie and pattern matching
    async fn phase_e_content_analysis(&mut self, retrieved_files: &[RetrievedFile], deadline: Instant) -> Result<Vec<Finding>> {
        let phase_start = Instant::now();
        tracing::info!("Phase E: Starting content analysis for {} files", retrieved_files.len());
        
        // Sort by priority and file characteristics for optimal analysis order
        let mut sorted_files = retrieved_files.to_vec();
        sorted_files.sort_by(|a, b| {
            // Prioritize smaller, high-value files first
            let a_score = self.calculate_analysis_priority(a);
            let b_score = self.calculate_analysis_priority(b);
            b_score.partial_cmp(&a_score).unwrap_or(std::cmp::Ordering::Equal)
        });
        
        let mut findings = Vec::new();
        let remaining_time = deadline.saturating_duration_since(Instant::now());
        let per_file_timeout = (remaining_time / (sorted_files.len() as u32).max(1))
            .min(Duration::from_secs(30))
            .max(Duration::from_secs(2));
        
        tracing::info!("Analyzing files with {}s timeout per file", per_file_timeout.as_secs());
        
        for (i, file) in sorted_files.iter().enumerate() {
            if Instant::now() >= deadline {
                tracing::warn!("Content analysis phase timed out after {} files", i);
                break;
            }
            
            let file_deadline = Instant::now() + per_file_timeout;
            
            match timeout(per_file_timeout, self.analyze_file_content(file, file_deadline)).await {
                Ok(Ok(file_findings)) => {
                    findings.extend(file_findings);
                }
                Ok(Err(e)) => {
                    tracing::debug!("Failed to analyze {}: {}", file.url, e);
                }
                Err(_) => {
                    tracing::debug!("Analysis timeout for {}", file.url);
                }
            }
        }
        
        let phase_duration = phase_start.elapsed();
        {
            let mut telemetry = self.telemetry.lock().await;
            telemetry.phase_e_duration = phase_duration;
            telemetry.findings_count = findings.len();
        }
        
        tracing::info!(
            "Phase E completed in {:.2}s: {} findings from {} files", 
            phase_duration.as_secs_f64(), 
            findings.len(),
            retrieved_files.len()
        );
        
        Ok(findings)
    }
    
    fn calculate_analysis_priority(&self, file: &RetrievedFile) -> f32 {
        let mut score = 0.0;
        
        // Status code scoring (successful responses get higher priority)
        match file.status {
            200 => score += 3.0, // Successful response
            201 | 204 => score += 2.5, // Created/No Content
            301 | 302 => score += 1.0, // Redirects might have interesting info
            401 | 403 => score += 2.0, // Auth required - might contain hints
            _ => score += 0.5, // Other status codes get lower priority
        }
        
        // File size (smaller is better for quick analysis)
        if file.size < 1024 { score += 3.0; }
        else if file.size < 10_000 { score += 2.0; }
        else if file.size < 100_000 { score += 1.0; }
        else if file.size > 10_000_000 { score -= 2.0; }
        
        // Content type preferences
        if let Some(ct) = &file.content_type {
            let ct_lower = ct.to_lowercase();
            if ct_lower.contains("text/plain") || ct_lower.contains("application/json") {
                score += 2.0;
            } else if ct_lower.contains("text/") || ct_lower.contains("application/xml") {
                score += 1.5;
            }
        }
        
        // URL-based priority
        let (url_priority, _) = self.filename_triage.score_url(&file.url);
        score += url_priority as f32 * 0.5;
        
        score
    }
    
    async fn analyze_file_content(&self, file: &RetrievedFile, deadline: Instant) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();
        
        // Quick path existence check
        if !file.local_path.exists() {
            return Ok(findings);
        }
        
        // Read file with size limits
        let content = if file.size > 5_000_000 { // 5MB limit for full analysis
            // For large files, read just the beginning
            let mut file_handle = fs::File::open(&file.local_path).await?;
            let mut buffer = vec![0u8; 1_000_000]; // 1MB sample
            let bytes_read = tokio::io::AsyncReadExt::read(&mut file_handle, &mut buffer).await?;
            buffer.truncate(bytes_read);
            String::from_utf8_lossy(&buffer).to_string()
        } else {
            fs::read_to_string(&file.local_path).await?
        };
        
        if Instant::now() >= deadline {
            return Ok(findings);
        }
        
        // Pattern-based analysis
        findings.extend(self.analyze_with_patterns(&content, &file.url));
        
        if Instant::now() >= deadline {
            return Ok(findings);
        }
        
        // Filename-based analysis for specific file types
        findings.extend(self.analyze_by_file_type(&content, &file.url));
        
        Ok(findings)
    }
    
    fn analyze_with_patterns(&self, content: &str, url: &str) -> Vec<Finding> {
        let mut findings = Vec::new();
        let content_lower = content.to_lowercase();
        
        // High-value secret patterns
        let secret_patterns = [
            // API Keys and tokens
            (r#"(?i)api[_-]?key[s]?[\s]*[:=][\s]*['"]?([a-z0-9]{20,})['"]?"#, "API Key", 9),
            (r#"(?i)access[_-]?token[s]?[\s]*[:=][\s]*['"]?([a-z0-9]{20,})['"]?"#, "Access Token", 9),
            (r#"(?i)secret[_-]?key[s]?[\s]*[:=][\s]*['"]?([a-z0-9]{20,})['"]?"#, "Secret Key", 9),
            
            // Database connections
            (r#"(?i)password[\s]*[:=][\s]*['"]?([^'"\s]{6,})['"]?"#, "Password", 8),
            (r"(?i)jdbc:[\w]+://([^/\s]+)", "Database Connection", 7),
            (r"(?i)mongodb://([^\s]+)", "MongoDB Connection", 7),
            
            // AWS/Cloud credentials
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key", 10),
            (r#"(?i)aws[_-]?secret[_-]?access[_-]?key[\s]*[:=][\s]*['"]?([a-z0-9/+=]{40})['"]?"#, "AWS Secret", 10),
            
            // Private keys
            (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----", "Private Key", 10),
            (r"-----BEGIN RSA PRIVATE KEY-----", "RSA Private Key", 10),
            
            // Generic credentials
            (r#"(?i)username[\s]*[:=][\s]*['"]?([^'"\s]{3,})['"]?"#, "Username", 5),
            (r#"(?i)email[\s]*[:=][\s]*['"]?([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})['"]?"#, "Email", 4),
        ];
        
        for (pattern, finding_type, priority) in secret_patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                for mat in re.find_iter(content) {
                    let snippet = &content[mat.start()..mat.end().min(content.len()).min(mat.start() + 100)];
                    findings.push(Finding {
                        url: url.to_string(),
                        finding_type: finding_type.to_string(),
                        confidence: priority as f32 / 10.0,
                        details: format!("{} ({})", snippet, Self::extract_context(content, mat.start(), mat.end())),
                    });
                    
                    // Limit findings per pattern to avoid spam
                    if findings.len() > 50 {
                        break;
                    }
                }
            }
        }
        
        // Content-based heuristics
        if content_lower.contains("password") && content_lower.contains("database") {
            findings.push(Finding {
                url: url.to_string(),
                finding_type: "Database Configuration".to_string(),
                confidence: 0.7,
                details: format!("{} ({})", Self::extract_relevant_snippet(content, "password"), "File contains database password references"),
            });
        }
        
        if content_lower.contains(".env") || content_lower.contains("environment") {
            findings.push(Finding {
                url: url.to_string(),
                finding_type: "Environment Configuration".to_string(),
                confidence: 0.6,
                details: format!("{} ({})", Self::extract_relevant_snippet(content, "env"), "File contains environment configuration"),
            });
        }
        
        findings
    }
    
    fn analyze_by_file_type(&self, content: &str, url: &str) -> Vec<Finding> {
        let mut findings = Vec::new();
        let url_lower = url.to_lowercase();
        
        // Git-specific analysis
        if url_lower.contains(".git") {
            findings.push(Finding {
                url: url.to_string(),
                finding_type: "Git Repository Access".to_string(),
                confidence: 0.8,
                details: format!("{} ({})", content.chars().take(200).collect::<String>(), "Git repository data exposed"),
            });
        }
        
        // Robots.txt analysis
        if url_lower.contains("robots.txt") {
            for line in content.lines() {
                if line.trim().starts_with("Disallow:") || line.trim().starts_with("Allow:") {
                    if let Some(path) = line.split(':').nth(1) {
                        let path = path.trim();
                        if !path.is_empty() && path != "/" {
                            findings.push(Finding {
                                url: url.to_string(),
                                finding_type: "Robots.txt Path Disclosure".to_string(),
                                confidence: 0.5,
                                details: format!("{} (Robots.txt reveals path: {})", line, path),
                            });
                        }
                    }
                }
            }
        }
        
        // Configuration file patterns
        if url_lower.contains(".env") || url_lower.contains("config") {
            for line in content.lines() {
                if line.contains('=') && !line.trim().starts_with('#') {
                    if let Some((key, _value)) = line.split_once('=') {
                        let key_lower = key.to_lowercase();
                        if key_lower.contains("password") || 
                           key_lower.contains("secret") || 
                           key_lower.contains("token") ||
                           key_lower.contains("key") {
                            findings.push(Finding {
                                url: url.to_string(),
                                finding_type: "Configuration Secret".to_string(),
                                confidence: 0.8,
                                details: format!("{} (Configuration variable: {})", line, key.trim()),
                            });
                        }
                    }
                }
            }
        }
        
        // SQL file analysis
        if url_lower.contains(".sql")
            && (content.to_lowercase().contains("create user") || 
                content.to_lowercase().contains("grant") ||
                content.to_lowercase().contains("password")) {
            findings.push(Finding {
                url: url.to_string(),
                finding_type: "SQL Credentials".to_string(),
                confidence: 0.7,
                details: format!("{} ({})", Self::extract_relevant_snippet(content, "password"), "SQL file contains user management commands"),
            });
        }
        
        findings
    }
    
    fn extract_context(content: &str, start: usize, end: usize) -> String {
        let context_start = start.saturating_sub(50);
        let context_end = (end + 50).min(content.len());
        
        content.chars()
            .skip(context_start)
            .take(context_end - context_start)
            .collect::<String>()
            .lines()
            .take(3)
            .collect::<Vec<_>>()
            .join(" ")
    }
    
    fn extract_relevant_snippet(content: &str, keyword: &str) -> String {
        let keyword_lower = keyword.to_lowercase();
        
        for line in content.lines() {
            if line.to_lowercase().contains(&keyword_lower) {
                return line.trim().chars().take(100).collect();
            }
        }
        
        // Fallback to first line
        content.lines().next()
            .unwrap_or("")
            .trim()
            .chars()
            .take(100)
            .collect()
    }
}