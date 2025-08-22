# ipcrawler Modernization Implementation Plan
## Complete UI/UX Enhancement with Modern Rust Crates

---

## 🎯 **Objective**
Transform ipcrawler from a traditional CLI tool into a modern, interactive reconnaissance platform with real-time TUI dashboard, smart notifications, beautiful output formatting, and enhanced user experience.

## 🔧 **Core Technologies to Integrate**

### Priority 1 - Essential UX
1. **ratatui** (0.28) - Real-time TUI dashboard
2. **comfy-table** (7.1) - Beautiful terminal tables
3. **dialoguer** (0.11) - Interactive prompts
4. **notify-rust** (4.11) - Desktop notifications
5. **which** (6.0) - Smart tool detection

### Priority 2 - Enhanced Experience  
6. **human-panic** (2.0) - User-friendly errors
7. **arboard** (3.4) - Clipboard integration
8. **open** (5.3) - Smart file opening

---

## 📋 **Implementation Rules**

### Global Rules (Apply to ALL Phases)
1. **NO breaking changes** - All existing CLI commands must continue working
2. **Feature flags** - New features must be behind feature flags initially
3. **Backward compatibility** - Existing YAML configs must work unchanged
4. **Build verification** - After EVERY phase: `cargo build --release && cargo build`
5. **Test existing functionality** - Run `./target/release/ipcrawler --dry-run -t test.com`
6. **Documentation** - Update relevant docs after each phase
7. **Git commits** - Create atomic commits after each successful phase
8. **Error handling** - All new features must gracefully degrade on failure
9. **NO TOOL-SPECIFIC HARDCODING** - Never hardcode specific tool names, paths, or commands in any implementation
10. **YAML-DRIVEN CONFIGURATION** - All tool information must come from YAML configuration files
11. **DYNAMIC TOOL HANDLING** - Use generic tool detection and execution patterns that work with any tool
12. **CONFIGURATION ABSTRACTION** - Tools are defined by their metadata (name, command, timeout) not their identity

---

## 🚀 **PHASE 1: Foundation & Table Enhancement**
*Enhance basic output with beautiful tables while maintaining compatibility*

### 🚫 PHASE 1 ANTI-HARDCODING RULES:
- Table builders must work with ANY tool results, not specific tool outputs
- Use generic field names (tool_name, status, duration) not tool-specific fields
- Discovery categorization must be metadata-driven, not hardcoded tool names
- All formatting logic must be based on result structure, not tool identity

### Phase 1.0: Add comfy-table dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
comfy-table = "7.1"
```

**Verification:**
```bash
cargo check
cargo tree | grep comfy-table
```

### Phase 1.1: Create table module
**File:** `src/table.rs` (NEW FILE)
```rust
use comfy_table::{Table, Cell, Attribute, Color, ContentArrangement};
use comfy_table::presets::UTF8_FULL;
use comfy_table::modifiers::UTF8_ROUND_CORNERS;

pub struct TableBuilder {
    table: Table,
}

impl TableBuilder {
    pub fn new() -> Self {
        let mut table = Table::new();
        table.load_preset(UTF8_FULL)
            .apply_modifier(UTF8_ROUND_CORNERS)
            .set_content_arrangement(ContentArrangement::Dynamic);
        
        Self { table }
    }
    
    pub fn discovery_summary(
        ports: &[String],
        services: &[String], 
        vulns: &[String]
    ) -> String {
        let mut builder = Self::new();
        
        builder.table.set_header(vec![
            Cell::new("Type").add_attribute(Attribute::Bold),
            Cell::new("Count").add_attribute(Attribute::Bold),
            Cell::new("Details").add_attribute(Attribute::Bold),
        ]);
        
        builder.table.add_row(vec![
            Cell::new("Ports").fg(Color::Green),
            Cell::new(ports.len().to_string()),
            Cell::new(ports.join(", ")),
        ]);
        
        builder.table.add_row(vec![
            Cell::new("Services").fg(Color::Blue),
            Cell::new(services.len().to_string()),
            Cell::new(services.join(", ")),
        ]);
        
        builder.table.add_row(vec![
            Cell::new("Vulnerabilities").fg(Color::Red),
            Cell::new(vulns.len().to_string()),
            Cell::new(vulns.join(", ")),
        ]);
        
        builder.table.to_string()
    }
    
    pub fn tool_execution_summary(results: &[crate::executor::ToolResult]) -> String {
        let mut builder = Self::new();
        
        builder.table.set_header(vec![
            Cell::new("Tool").add_attribute(Attribute::Bold),
            Cell::new("Status").add_attribute(Attribute::Bold),
            Cell::new("Duration").add_attribute(Attribute::Bold),
            Cell::new("Output Size").add_attribute(Attribute::Bold),
        ]);
        
        for result in results {
            let status_cell = if result.success {
                Cell::new("✓ Success").fg(Color::Green)
            } else {
                Cell::new("✗ Failed").fg(Color::Red)
            };
            
            builder.table.add_row(vec![
                Cell::new(&result.tool_name),
                status_cell,
                Cell::new(format!("{:.2}s", result.duration.as_secs_f64())),
                Cell::new(format!("{} bytes", result.stdout.len())),
            ]);
        }
        
        builder.table.to_string()
    }
}
```

**Verification:**
```bash
echo "pub mod table;" >> src/lib.rs  # If lib.rs exists
# OR add to main.rs: mod table;
cargo check
```

### Phase 1.2: Integrate tables into main output
**File:** `src/main.rs`
**Location:** After line ~300 (after scan completion)
```rust
// Add module declaration at top
mod table;

// In run_scan function, after results are collected:
// Find the section that prints "Scan complete"
// ADD this code:

if args.verbose {
    progress.print_section("📊 Scan Summary");
    
    // Collect discoveries (adapt to your actual data structures)
    let ports: Vec<String> = output_handler.discoveries.iter()
        .filter_map(|d| match d.discovery_type {
            DiscoveryType::Port => Some(d.value.clone()),
            _ => None
        })
        .collect();
    
    let services: Vec<String> = output_handler.discoveries.iter()
        .filter_map(|d| match d.discovery_type {
            DiscoveryType::Service => Some(d.value.clone()),
            _ => None
        })
        .collect();
    
    let vulns: Vec<String> = output_handler.discoveries.iter()
        .filter_map(|d| match d.discovery_type {
            DiscoveryType::Vulnerability => Some(d.value.clone()),
            _ => None
        })
        .collect();
    
    // Print beautiful table
    println!("{}", table::TableBuilder::discovery_summary(&ports, &services, &vulns));
    
    // Tool execution summary
    println!("\n📈 Tool Execution Report");
    println!("{}", table::TableBuilder::tool_execution_summary(&results));
}
```

### Phase 1.3: Build and test
```bash
cargo build --release
cargo build  # Debug build
./target/release/ipcrawler -t 127.0.0.1 --dry-run --verbose
```

**Expected Output:**
- Normal scan output PLUS beautiful tables when --verbose is used
- No breaking changes to existing output

### Phase 1.4: Verification checklist
- [ ] comfy-table added to Cargo.toml
- [ ] table.rs module created and compiles
- [ ] Tables appear with --verbose flag
- [ ] Normal output unchanged without --verbose
- [ ] Both release and debug builds succeed
- [ ] Dry run works correctly

---

## 🚀 **PHASE 2: Smart Tool Detection**
*Enhance tool discovery and provide better feedback*

### 🚫 PHASE 2 ANTI-HARDCODING RULES:
- NO hardcoded tool names in match statements or string comparisons
- Alternative tool suggestions MUST come from YAML metadata, not hardcoded lists
- Tool categorization must be driven by configuration metadata, not tool names
- Path detection must work generically with any executable name from YAML

### Phase 2.0: Add which dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
which = "6.0"
```

### Phase 2.1: Enhance doctor module
**File:** `src/doctor.rs`
**Location:** In `DependencyChecker` impl
```rust
use which::which;

impl DependencyChecker {
    // ADD new method
    pub fn find_tool_path(&self, tool_name: &str) -> Option<PathBuf> {
        which(tool_name).ok()
    }
    
    // 🚫 ANTI-HARDCODING: Generic tool alternative discovery
    pub fn find_alternative_tool(&self, tool_config: &ToolConfig) -> Option<String> {
        // CORRECT: Use alternatives from YAML configuration
        let alternatives = tool_config.metadata
            .get("alternatives")
            .and_then(|alt| alt.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>())
            .unwrap_or_default();
        
        for alt in alternatives {
            if which(alt).is_ok() {
                return Some(alt.to_string());
            }
        }
        None
    }
    
    pub fn get_tool_version(&self, tool_name: &str) -> Option<String> {
        let path = self.find_tool_path(tool_name)?;
        
        // Try common version flags
        for flag in &["--version", "-v", "-V", "version"] {
            if let Ok(output) = Command::new(&path)
                .arg(flag)
                .output()
            {
                if output.status.success() {
                    let version = String::from_utf8_lossy(&output.stdout);
                    if !version.trim().is_empty() {
                        return Some(version.lines().next()?.to_string());
                    }
                }
            }
        }
        None
    }
}
```

### Phase 2.2: Enhance tool validation
**File:** `src/config.rs`
**Location:** In validate() method
```rust
use crate::doctor::DependencyChecker;

impl Config {
    pub fn validate(&self) -> Result<(), String> {
        // ... existing validation ...
        
        // ADD tool availability checking
        let checker = DependencyChecker::new();
        let mut warnings = Vec::new();
        
        for tool in &self.tools {
            if tool.enabled {
                // Extract base command from tool.command
                let base_cmd = tool.command.split_whitespace()
                    .next()
                    .unwrap_or("");
                
                if checker.find_tool_path(base_cmd).is_none() {
                    if let Some(alternative) = checker.find_alternative_tool(base_cmd) {
                        warnings.push(format!(
                            "⚠️ Tool '{}' not found. Consider using '{}' instead",
                            base_cmd, alternative
                        ));
                    } else {
                        warnings.push(format!(
                            "⚠️ Tool '{}' not found and no alternatives available",
                            base_cmd
                        ));
                    }
                }
            }
        }
        
        // Print warnings but don't fail
        for warning in warnings {
            eprintln!("{}", warning);
        }
        
        Ok(())
    }
}
```

### Phase 2.3: Build and test
```bash
cargo build --release
cargo build
./target/release/ipcrawler --validate
./target/release/ipcrawler --doctor
```

### Phase 2.4: Verification checklist
- [ ] which crate added successfully
- [ ] Tool path detection works
- [ ] Alternative tool suggestions appear
- [ ] Version detection functional
- [ ] Validation shows warnings for missing tools
- [ ] No breaking changes

---

## 🚀 **PHASE 3: Interactive Prompts**
*Replace Y/N prompts with rich interactions*

### 🚫 PHASE 3 ANTI-HARDCODING RULES:
- Prompts must be generic and tool-agnostic
- Configuration selection must work with any YAML profile, not hardcoded options
- Profile descriptions and choices must be dynamically loaded from YAML metadata
- NO hardcoded scan type names or tool-specific prompt text

### Phase 3.0: Add dialoguer dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
dialoguer = "0.11"
```

### Phase 3.1: Create interaction module
**File:** `src/interaction.rs` (NEW FILE)
```rust
use dialoguer::{Confirm, Select, MultiSelect, Input, theme::ColorfulTheme};
use std::path::PathBuf;

pub struct InteractionManager {
    theme: ColorfulTheme,
}

impl InteractionManager {
    pub fn new() -> Self {
        Self {
            theme: ColorfulTheme::default(),
        }
    }
    
    pub fn confirm(&self, prompt: &str, default: bool) -> bool {
        Confirm::with_theme(&self.theme)
            .with_prompt(prompt)
            .default(default)
            .interact()
            .unwrap_or(default)
    }
    
    pub fn select_report_formats(&self) -> Vec<String> {
        let formats = vec!["JSON", "HTML", "Markdown", "Text", "All"];
        
        let selection = MultiSelect::with_theme(&self.theme)
            .with_prompt("Select report formats to generate")
            .items(&formats)
            .defaults(&[true, true, true, true])
            .interact()
            .unwrap_or_else(|_| vec![0, 1, 2, 3]);
        
        selection.iter()
            .map(|&i| formats[i].to_lowercase())
            .collect()
    }
    
    pub fn select_tools(&self, available_tools: &[String]) -> Vec<String> {
        if available_tools.is_empty() {
            return vec![];
        }
        
        let selections = MultiSelect::with_theme(&self.theme)
            .with_prompt("Select tools to run")
            .items(available_tools)
            .interact()
            .unwrap_or_else(|_| (0..available_tools.len()).collect());
        
        selections.iter()
            .map(|&i| available_tools[i].clone())
            .collect()
    }
    
    pub fn get_custom_output_dir(&self, default: &str) -> PathBuf {
        let input: String = Input::with_theme(&self.theme)
            .with_prompt("Output directory")
            .default(default.to_string())
            .interact_text()
            .unwrap_or_else(|_| default.to_string());
        
        PathBuf::from(input)
    }
    
    pub fn select_scan_profile(&self, profiles: &[String]) -> Option<String> {
        if profiles.is_empty() {
            return None;
        }
        
        let selection = Select::with_theme(&self.theme)
            .with_prompt("Select scan profile")
            .items(profiles)
            .default(0)
            .interact_opt()
            .unwrap_or(None);
        
        selection.map(|i| profiles[i].clone())
    }
}
```

### Phase 3.2: Replace existing prompts
**File:** `src/progress.rs`
**Location:** In prompt_user_yn method
```rust
use crate::interaction::InteractionManager;

impl ProgressManager {
    pub fn prompt_user_yn(&self, question: &str, default_yes: bool) -> bool {
        // Check if we're in non-interactive mode
        if std::env::var("IPCRAWLER_NON_INTERACTIVE").is_ok() {
            return default_yes;
        }
        
        // Try new interactive prompt first
        if let Ok(interaction) = std::panic::catch_unwind(|| {
            let manager = InteractionManager::new();
            manager.confirm(question, default_yes)
        }) {
            return interaction;
        }
        
        // Fallback to existing implementation
        use std::io::{self, Write};
        let default_char = if default_yes { "Y/n" } else { "y/N" };
        print!("📖 {} [{}]: ", question, default_char);
        io::stdout().flush().unwrap_or(());
        
        let mut input = String::new();
        match io::stdin().read_line(&mut input) {
            Ok(_) => {
                let response = input.trim().to_lowercase();
                match response.as_str() {
                    "y" | "yes" => true,
                    "n" | "no" => false,
                    "" => default_yes,
                    _ => default_yes,
                }
            }
            Err(_) => default_yes,
        }
    }
}
```

### Phase 3.3: Add interactive mode flag
**File:** `src/cli.rs`
**Location:** In Cli struct
```rust
#[derive(Parser, Debug)]
pub struct Cli {
    // ... existing fields ...
    
    #[arg(long = "interactive", short = 'i', help = "Enable interactive mode with rich prompts")]
    pub interactive: bool,
    
    #[arg(long = "non-interactive", help = "Disable all interactive prompts")]
    pub non_interactive: bool,
}
```

### Phase 3.4: Integrate interactive mode
**File:** `src/main.rs`
**Location:** At start of main() or run_scan()
```rust
// Add module
mod interaction;

// In main() or run_scan():
if args.non_interactive {
    std::env::set_var("IPCRAWLER_NON_INTERACTIVE", "1");
} else if args.interactive {
    std::env::set_var("IPCRAWLER_INTERACTIVE", "1");
    
    // Optional: Allow tool selection in interactive mode
    let interaction = interaction::InteractionManager::new();
    
    // If no config specified, show profile selector
    if args.config.is_empty() || args.config == vec!["default"] {
        let paths = paths::ReconPaths::new()?;
        let available_configs = paths.list_available_configs();
        let profile_names: Vec<String> = available_configs.iter()
            .map(|(name, _)| name.clone())
            .collect();
        
        if let Some(selected) = interaction.select_scan_profile(&profile_names) {
            // Override config with selection
            // This would need adjustment based on your actual config handling
            println!("Selected profile: {}", selected);
        }
    }
}
```

### Phase 3.5: Build and test
```bash
cargo build --release
cargo build

# Test interactive mode
./target/release/ipcrawler -t 127.0.0.1 --interactive --dry-run

# Test non-interactive mode
./target/release/ipcrawler -t 127.0.0.1 --non-interactive --dry-run

# Test normal mode (fallback)
./target/release/ipcrawler -t 127.0.0.1 --dry-run
```

### Phase 3.6: Verification checklist
- [ ] dialoguer added successfully
- [ ] Interactive prompts work in --interactive mode
- [ ] Non-interactive mode bypasses all prompts
- [ ] Normal mode uses fallback prompts
- [ ] Tool selection works (if implemented)
- [ ] Profile selection works (if implemented)
- [ ] No breaking changes to existing CLI

---

## 🚀 **PHASE 4: Desktop Notifications**
*Add native OS notifications for scan events*

### 🚫 PHASE 4 ANTI-HARDCODING RULES:
- Notification messages must be generic and tool-agnostic
- Scan results in notifications must not reference specific tools by name
- Success/failure notifications must work with any tool configuration
- Notification content must be based on metadata, not hardcoded tool-specific text

### Phase 4.0: Add notify-rust dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
notify-rust = "4.11"
```

### Phase 4.1: Create notification module
**File:** `src/notification.rs` (NEW FILE)
```rust
use notify_rust::{Notification, Urgency, Timeout};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

pub struct NotificationManager {
    enabled: Arc<AtomicBool>,
    app_name: String,
}

impl NotificationManager {
    pub fn new() -> Self {
        Self {
            enabled: Arc::new(AtomicBool::new(true)),
            app_name: "ipcrawler".to_string(),
        }
    }
    
    pub fn set_enabled(&self, enabled: bool) {
        self.enabled.store(enabled, Ordering::Relaxed);
    }
    
    fn should_notify(&self) -> bool {
        self.enabled.load(Ordering::Relaxed) &&
        std::env::var("IPCRAWLER_NOTIFICATIONS").unwrap_or_else(|_| "true".to_string()) != "false"
    }
    
    pub fn scan_started(&self, target: &str) {
        if !self.should_notify() { return; }
        
        let _ = Notification::new()
            .appname(&self.app_name)
            .summary("🎯 Scan Started")
            .body(&format!("Starting reconnaissance on {}", target))
            .icon("security-medium")
            .timeout(Timeout::Milliseconds(3000))
            .show();
    }
    
    pub fn scan_completed(&self, target: &str, duration: std::time::Duration) {
        if !self.should_notify() { return; }
        
        let _ = Notification::new()
            .appname(&self.app_name)
            .summary("✅ Scan Complete")
            .body(&format!(
                "Target: {}\nDuration: {:.1} seconds\nResults saved",
                target,
                duration.as_secs_f64()
            ))
            .icon("security-high")
            .urgency(Urgency::Normal)
            .timeout(Timeout::Milliseconds(5000))
            .show();
    }
    
    pub fn critical_finding(&self, finding: &str) {
        if !self.should_notify() { return; }
        
        let _ = Notification::new()
            .appname(&self.app_name)
            .summary("🚨 Critical Finding")
            .body(finding)
            .icon("dialog-warning")
            .urgency(Urgency::Critical)
            .timeout(Timeout::Never)
            .show();
    }
    
    pub fn tool_failed(&self, tool_name: &str, error: &str) {
        if !self.should_notify() { return; }
        
        let _ = Notification::new()
            .appname(&self.app_name)
            .summary("⚠️ Tool Failed")
            .body(&format!("{} failed: {}", tool_name, error))
            .icon("dialog-error")
            .urgency(Urgency::Normal)
            .timeout(Timeout::Milliseconds(4000))
            .show();
    }
    
    pub fn discovery(&self, discovery_type: &str, count: usize) {
        if !self.should_notify() { return; }
        if count == 0 { return; }
        
        let icon = match discovery_type {
            "ports" => "network-wired",
            "services" => "applications-system",
            "vulnerabilities" => "security-low",
            _ => "dialog-information"
        };
        
        let _ = Notification::new()
            .appname(&self.app_name)
            .summary(&format!("📡 {} Discovered", discovery_type))
            .body(&format!("Found {} new {}", count, discovery_type))
            .icon(icon)
            .timeout(Timeout::Milliseconds(3000))
            .show();
    }
}
```

### Phase 4.2: Add notification flag
**File:** `src/cli.rs`
```rust
#[derive(Parser, Debug)]
pub struct Cli {
    // ... existing fields ...
    
    #[arg(long = "notify", help = "Enable desktop notifications")]
    pub notify: bool,
    
    #[arg(long = "no-notify", help = "Disable desktop notifications")]
    pub no_notify: bool,
}
```

### Phase 4.3: Integrate notifications
**File:** `src/main.rs`
**Location:** Throughout scan execution
```rust
// Add module
mod notification;

// In run_scan function:
// Create notification manager
let notifier = notification::NotificationManager::new();

// Configure based on CLI flags
if args.no_notify {
    notifier.set_enabled(false);
} else if args.notify {
    notifier.set_enabled(true);
}

// At scan start:
notifier.scan_started(&target);
let scan_start = std::time::Instant::now();

// When discoveries are made (in executor or pipeline):
// This would need to be passed to executor/pipeline
if new_ports_discovered > 0 {
    notifier.discovery("ports", new_ports_discovered);
}

// On tool failure:
if !result.success {
    notifier.tool_failed(&result.tool_name, &result.stderr);
}

// On critical vulnerability found:
// You'd check discoveries for critical severity
for discovery in &discoveries {
    if discovery.discovery_type == DiscoveryType::Vulnerability {
        if discovery.metadata.get("severity").and_then(|v| v.as_str()) == Some("critical") {
            notifier.critical_finding(&discovery.value);
        }
    }
}

// At scan completion:
let scan_duration = scan_start.elapsed();
notifier.scan_completed(&target, scan_duration);
```

### Phase 4.4: Build and test
```bash
cargo build --release
cargo build

# Test with notifications
./target/release/ipcrawler -t 127.0.0.1 --notify --dry-run

# Test without notifications
./target/release/ipcrawler -t 127.0.0.1 --no-notify --dry-run

# Test on different platforms
# macOS: Should see native notifications
# Linux: Requires notification daemon (usually present in desktop environments)
# Windows: Should see Windows notifications
```

### Phase 4.5: Verification checklist
- [ ] notify-rust added successfully
- [ ] Notifications appear with --notify flag
- [ ] No notifications with --no-notify flag
- [ ] Scan start/complete notifications work
- [ ] Tool failure notifications work
- [ ] Discovery notifications work
- [ ] Works on current OS
- [ ] Graceful fallback if notifications unavailable

---

## 🚀 **PHASE 5: User-Friendly Panic Handler**
*Replace scary panic messages with helpful ones*

### 🚫 PHASE 5 ANTI-HARDCODING RULES:
- Error messages must not reference specific tools or commands by name
- Troubleshooting suggestions must be generic and configuration-driven
- Recovery hints must work regardless of which tool caused the failure
- Bug report generation must be tool-agnostic

### Phase 5.0: Add human-panic dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
human-panic = "2.0"
```

### Phase 5.1: Setup panic handler
**File:** `src/main.rs`
**Location:** At very start of main()
```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Setup human panic handler for release builds
    #[cfg(not(debug_assertions))]
    {
        human_panic::setup_panic!();
    }
    
    // In debug mode, keep normal panic for debugging
    #[cfg(debug_assertions)]
    {
        std::env::set_var("RUST_BACKTRACE", "1");
    }
    
    // Rest of main function...
}
```

### Phase 5.2: Add custom metadata
**File:** `Cargo.toml`
```toml
[package.metadata.human-panic]
homepage = "https://github.com/yourusername/ipcrawler"
repository = "https://github.com/yourusername/ipcrawler"
```

### Phase 5.3: Build and test
```bash
cargo build --release
cargo build

# Test panic handling (create a test that panics)
# In release mode, should see friendly message
# In debug mode, should see full backtrace
```

### Phase 5.4: Verification checklist
- [ ] human-panic added successfully
- [ ] Release builds show friendly panic messages
- [ ] Debug builds show full backtraces
- [ ] Bug report information included
- [ ] No impact on normal operation

---

## 🚦 **PHASE 6: TUI Dashboard (STOP FOR HUMAN TESTING)**
*Interactive real-time dashboard - requires human interaction testing*

### 🚫 PHASE 6 ANTI-HARDCODING RULES:
- TUI components must display ANY tool results, not specific tool outputs
- Dashboard widgets must be generic and data-driven, not tool-specific
- Progress bars and status indicators must work with any YAML-configured tool
- Tool result parsing must be based on output structure, not tool identity
- No hardcoded widget layouts for specific scan types

### Phase 6.0: Add ratatui dependencies
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
ratatui = "0.28"
crossterm = "0.28"

[features]
default = []
tui = ["dep:ratatui", "dep:crossterm"]
```

### Phase 6.1: Create TUI module structure
**File:** `src/tui/mod.rs` (NEW FILE)
```rust
pub mod app;
pub mod ui;
pub mod dashboard;
pub mod event;

pub use app::TuiApp;
pub use dashboard::Dashboard;
```

### Phase 6.2: Create TUI app state
**File:** `src/tui/app.rs` (NEW FILE)
```rust
use std::sync::{Arc, Mutex};
use crate::executor::ToolResult;
use crate::output::Discovery;

#[derive(Debug, Clone)]
pub enum AppState {
    Idle,
    Scanning { target: String, start_time: std::time::Instant },
    Paused,
    Completed,
}

pub struct TuiApp {
    pub state: AppState,
    pub target: String,
    pub active_tools: Vec<String>,
    pub completed_tools: Vec<String>,
    pub discoveries: Arc<Mutex<Vec<Discovery>>>,
    pub tool_results: Arc<Mutex<Vec<ToolResult>>>,
    pub selected_tab: usize,
    pub should_quit: bool,
}

impl TuiApp {
    pub fn new(target: String) -> Self {
        Self {
            state: AppState::Idle,
            target,
            active_tools: Vec::new(),
            completed_tools: Vec::new(),
            discoveries: Arc::new(Mutex::new(Vec::new())),
            tool_results: Arc::new(Mutex::new(Vec::new())),
            selected_tab: 0,
            should_quit: false,
        }
    }
    
    pub fn start_scan(&mut self) {
        self.state = AppState::Scanning {
            target: self.target.clone(),
            start_time: std::time::Instant::now(),
        };
    }
    
    pub fn add_discovery(&self, discovery: Discovery) {
        if let Ok(mut discoveries) = self.discoveries.lock() {
            discoveries.push(discovery);
        }
    }
    
    pub fn add_tool_result(&self, result: ToolResult) {
        if let Ok(mut results) = self.tool_results.lock() {
            results.push(result);
        }
    }
    
    pub fn toggle_pause(&mut self) {
        self.state = match self.state {
            AppState::Scanning { .. } => AppState::Paused,
            AppState::Paused => {
                AppState::Scanning {
                    target: self.target.clone(),
                    start_time: std::time::Instant::now(),
                }
            }
            state => state,
        };
    }
}
```

### Phase 6.3: Create UI rendering
**File:** `src/tui/ui.rs` (NEW FILE)
```rust
use ratatui::{
    Frame,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, List, ListItem, Paragraph, Tabs},
};
use crate::tui::app::TuiApp;

pub fn draw(frame: &mut Frame, app: &TuiApp) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Header
            Constraint::Length(3),  // Tabs
            Constraint::Min(0),     // Main content
            Constraint::Length(3),  // Status bar
        ])
        .split(frame.area());
    
    // Header
    draw_header(frame, chunks[0], app);
    
    // Tabs
    draw_tabs(frame, chunks[1], app);
    
    // Main content based on selected tab
    match app.selected_tab {
        0 => draw_overview(frame, chunks[2], app),
        1 => draw_discoveries(frame, chunks[2], app),
        2 => draw_tools(frame, chunks[2], app),
        3 => draw_logs(frame, chunks[2], app),
        _ => {}
    }
    
    // Status bar
    draw_status_bar(frame, chunks[3], app);
}

fn draw_header(frame: &mut Frame, area: Rect, app: &TuiApp) {
    let header = Paragraph::new(vec![
        Line::from(vec![
            Span::styled("🎯 ipcrawler ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("| Target: "),
            Span::styled(&app.target, Style::default().fg(Color::Yellow)),
        ]),
    ])
    .block(Block::default().borders(Borders::ALL));
    
    frame.render_widget(header, area);
}

fn draw_tabs(frame: &mut Frame, area: Rect, app: &TuiApp) {
    let titles = vec!["Overview", "Discoveries", "Tools", "Logs"];
    let tabs = Tabs::new(titles)
        .block(Block::default().borders(Borders::ALL))
        .select(app.selected_tab)
        .style(Style::default().fg(Color::White))
        .highlight_style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD));
    
    frame.render_widget(tabs, area);
}

fn draw_overview(frame: &mut Frame, area: Rect, app: &TuiApp) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(area);
    
    // Left side - Active tools
    let active_tools: Vec<ListItem> = app.active_tools
        .iter()
        .map(|tool| ListItem::new(format!("⟳ {}", tool)))
        .collect();
    
    let active_list = List::new(active_tools)
        .block(Block::default().title("Active Tools").borders(Borders::ALL))
        .style(Style::default().fg(Color::Green));
    
    frame.render_widget(active_list, chunks[0]);
    
    // Right side - Statistics
    let discoveries = app.discoveries.lock().unwrap();
    let stats = vec![
        Line::from(format!("Ports: {}", discoveries.iter().filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Port)).count())),
        Line::from(format!("Services: {}", discoveries.iter().filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Service)).count())),
        Line::from(format!("Vulnerabilities: {}", discoveries.iter().filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Vulnerability)).count())),
    ];
    
    let stats_paragraph = Paragraph::new(stats)
        .block(Block::default().title("Statistics").borders(Borders::ALL));
    
    frame.render_widget(stats_paragraph, chunks[1]);
}

fn draw_discoveries(frame: &mut Frame, area: Rect, app: &TuiApp) {
    let discoveries = app.discoveries.lock().unwrap();
    let items: Vec<ListItem> = discoveries
        .iter()
        .map(|d| {
            let style = match d.discovery_type {
                crate::output::DiscoveryType::Port => Style::default().fg(Color::Green),
                crate::output::DiscoveryType::Service => Style::default().fg(Color::Blue),
                crate::output::DiscoveryType::Vulnerability => Style::default().fg(Color::Red),
                _ => Style::default(),
            };
            ListItem::new(format!("{:?}: {}", d.discovery_type, d.value)).style(style)
        })
        .collect();
    
    let list = List::new(items)
        .block(Block::default().title("Discoveries").borders(Borders::ALL));
    
    frame.render_widget(list, area);
}

fn draw_tools(frame: &mut Frame, area: Rect, app: &TuiApp) {
    let results = app.tool_results.lock().unwrap();
    let items: Vec<ListItem> = results
        .iter()
        .map(|r| {
            let status = if r.success { "✓" } else { "✗" };
            let style = if r.success {
                Style::default().fg(Color::Green)
            } else {
                Style::default().fg(Color::Red)
            };
            ListItem::new(format!("{} {} - {:.2}s", status, r.tool_name, r.duration.as_secs_f64()))
                .style(style)
        })
        .collect();
    
    let list = List::new(items)
        .block(Block::default().title("Tool Results").borders(Borders::ALL));
    
    frame.render_widget(list, area);
}

fn draw_logs(frame: &mut Frame, area: Rect, _app: &TuiApp) {
    let logs = Paragraph::new("Logs will appear here...")
        .block(Block::default().title("Logs").borders(Borders::ALL));
    
    frame.render_widget(logs, area);
}

fn draw_status_bar(frame: &mut Frame, area: Rect, app: &TuiApp) {
    let status = match &app.state {
        crate::tui::app::AppState::Idle => "Idle",
        crate::tui::app::AppState::Scanning { .. } => "Scanning",
        crate::tui::app::AppState::Paused => "Paused",
        crate::tui::app::AppState::Completed => "Completed",
    };
    
    let status_bar = Paragraph::new(Line::from(vec![
        Span::raw("Status: "),
        Span::styled(status, Style::default().fg(Color::Yellow)),
        Span::raw(" | "),
        Span::raw("[q]uit [p]ause [Tab] switch"),
    ]))
    .block(Block::default().borders(Borders::ALL));
    
    frame.render_widget(status_bar, area);
}
```

### Phase 6.4: Create event handler
**File:** `src/tui/event.rs` (NEW FILE)
```rust
use crossterm::event::{self, Event, KeyCode, KeyEvent};
use std::time::Duration;

pub enum AppEvent {
    Key(KeyEvent),
    Tick,
}

pub struct EventHandler {
    tick_rate: Duration,
}

impl EventHandler {
    pub fn new(tick_rate: Duration) -> Self {
        Self { tick_rate }
    }
    
    pub fn next(&self) -> Result<AppEvent, Box<dyn std::error::Error>> {
        if event::poll(self.tick_rate)? {
            match event::read()? {
                Event::Key(key) => Ok(AppEvent::Key(key)),
                _ => Ok(AppEvent::Tick),
            }
        } else {
            Ok(AppEvent::Tick)
        }
    }
}

pub fn handle_key_event(key: KeyEvent, app: &mut crate::tui::app::TuiApp) {
    match key.code {
        KeyCode::Char('q') | KeyCode::Esc => app.should_quit = true,
        KeyCode::Char('p') => app.toggle_pause(),
        KeyCode::Tab => {
            app.selected_tab = (app.selected_tab + 1) % 4;
        }
        _ => {}
    }
}
```

### Phase 6.5: Create dashboard runner
**File:** `src/tui/dashboard.rs` (NEW FILE)
```rust
use ratatui::{DefaultTerminal, Terminal};
use crossterm::{
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use std::io;
use std::time::Duration;
use crate::tui::{app::TuiApp, ui, event::{EventHandler, AppEvent, handle_key_event}};

pub struct Dashboard {
    terminal: DefaultTerminal,
    app: TuiApp,
    event_handler: EventHandler,
}

impl Dashboard {
    pub fn new(target: String) -> Result<Self, Box<dyn std::error::Error>> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen)?;
        
        let terminal = Terminal::new(ratatui::backend::CrosstermBackend::new(stdout))?;
        let app = TuiApp::new(target);
        let event_handler = EventHandler::new(Duration::from_millis(250));
        
        Ok(Self {
            terminal,
            app,
            event_handler,
        })
    }
    
    pub fn run(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        loop {
            self.terminal.draw(|frame| ui::draw(frame, &self.app))?;
            
            match self.event_handler.next()? {
                AppEvent::Key(key) => handle_key_event(key, &mut self.app),
                AppEvent::Tick => {}
            }
            
            if self.app.should_quit {
                break;
            }
        }
        
        Ok(())
    }
    
    pub fn get_app(&self) -> &TuiApp {
        &self.app
    }
    
    pub fn get_app_mut(&mut self) -> &mut TuiApp {
        &mut self.app
    }
}

impl Drop for Dashboard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), LeaveAlternateScreen);
    }
}
```

### Phase 6.6: Add TUI flag to CLI
**File:** `src/cli.rs`
```rust
#[derive(Parser, Debug)]
pub struct Cli {
    // ... existing fields ...
    
    #[arg(long = "tui", help = "Launch interactive TUI dashboard")]
    pub tui: bool,
}
```

### Phase 6.7: Integrate TUI mode
**File:** `src/main.rs`
```rust
// Add conditional compilation
#[cfg(feature = "tui")]
mod tui;

// In main() or run_scan():
#[cfg(feature = "tui")]
if args.tui {
    // Launch TUI mode
    let mut dashboard = tui::Dashboard::new(target.clone())?;
    
    // TODO: Connect executor to dashboard
    // This requires refactoring executor to send updates to dashboard
    
    dashboard.run()?;
    return Ok(());
}
```

### Phase 6.8: Build with TUI feature
```bash
# Build with TUI feature
cargo build --release --features tui
cargo build --features tui

# Test TUI mode
./target/release/ipcrawler -t 127.0.0.1 --tui
```

### ⚠️ **STOP HERE FOR HUMAN TESTING**
```
==========================================
HUMAN INTERACTION REQUIRED
==========================================

The TUI dashboard is now ready for testing. Please:

1. Run: ./target/release/ipcrawler -t 127.0.0.1 --tui
2. Test keyboard navigation:
   - Tab: Switch between tabs
   - q/Esc: Quit
   - p: Pause/Resume
3. Check visual layout on your terminal
4. Verify all panels render correctly
5. Test with different terminal sizes

Please provide feedback on:
- Layout issues
- Color scheme preferences  
- Missing features
- Performance issues
- Any crashes or rendering problems

After testing, provide your feedback and we'll continue with:
- Connecting the executor to update the TUI in real-time
- Adding more interactive features
- Implementing data filtering and searching
```

---

## 🚀 **PHASE 7: Clipboard Integration**
*Quick copy results to clipboard*

### 🚫 PHASE 7 ANTI-HARDCODING RULES:
- Clipboard content must be generic and work with any tool output
- No hardcoded formats specific to particular tools (nmap XML, etc.)
- Copy functionality must work with any structured data from any tool
- Format selection must be metadata-driven, not tool-specific

### Phase 7.0: Add arboard dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
arboard = "3.4"
```

### Phase 7.1: Create clipboard module
**File:** `src/clipboard.rs` (NEW FILE)
```rust
use arboard::Clipboard;
use std::sync::Mutex;

lazy_static::lazy_static! {
    static ref CLIPBOARD: Mutex<Option<Clipboard>> = Mutex::new(Clipboard::new().ok());
}

pub struct ClipboardManager;

impl ClipboardManager {
    pub fn copy_to_clipboard(text: &str) -> Result<(), String> {
        let mut clipboard_guard = CLIPBOARD.lock().map_err(|e| e.to_string())?;
        
        if let Some(ref mut clipboard) = *clipboard_guard {
            clipboard.set_text(text).map_err(|e| e.to_string())?;
            Ok(())
        } else {
            Err("Clipboard not available".to_string())
        }
    }
    
    pub fn copy_discoveries(discoveries: &[crate::output::Discovery]) -> Result<(), String> {
        let text = discoveries.iter()
            .map(|d| format!("{:?}: {}", d.discovery_type, d.value))
            .collect::<Vec<_>>()
            .join("\n");
        
        Self::copy_to_clipboard(&text)
    }
    
    pub fn copy_ports(ports: &[String]) -> Result<(), String> {
        let text = ports.join(",");
        Self::copy_to_clipboard(&text)
    }
    
    pub fn copy_summary(summary: &crate::output::ScanSummary) -> Result<(), String> {
        let text = format!(
            "Target: {}\nPorts: {}\nServices: {}\nVulnerabilities: {}\nDuration: {:.2}s",
            summary.target,
            summary.discoveries.iter().filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Port)).count(),
            summary.discoveries.iter().filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Service)).count(),
            summary.discoveries.iter().filter(|d| matches!(d.discovery_type, crate::output::DiscoveryType::Vulnerability)).count(),
            summary.metadata.get("duration").and_then(|v| v.as_f64()).unwrap_or(0.0)
        );
        
        Self::copy_to_clipboard(&text)
    }
}
```

### Phase 7.2: Add lazy_static
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
lazy_static = "1.5"
```

### Phase 7.3: Add clipboard commands
**File:** `src/cli.rs`
```rust
#[derive(Parser, Debug)]
pub struct Cli {
    // ... existing fields ...
    
    #[arg(long = "copy-ports", help = "Copy discovered ports to clipboard after scan")]
    pub copy_ports: bool,
    
    #[arg(long = "copy-summary", help = "Copy scan summary to clipboard after scan")]
    pub copy_summary: bool,
}
```

### Phase 7.4: Integrate clipboard
**File:** `src/main.rs`
```rust
// Add module
mod clipboard;

// After scan completion, before showing results:
if args.copy_ports {
    let ports: Vec<String> = output_handler.discoveries.iter()
        .filter_map(|d| match d.discovery_type {
            DiscoveryType::Port => Some(d.value.clone()),
            _ => None
        })
        .collect();
    
    match clipboard::ClipboardManager::copy_ports(&ports) {
        Ok(_) => progress.print_success("✂️ Ports copied to clipboard"),
        Err(e) => progress.print_warning(&format!("Failed to copy to clipboard: {}", e)),
    }
}

if args.copy_summary {
    match clipboard::ClipboardManager::copy_summary(&summary) {
        Ok(_) => progress.print_success("✂️ Summary copied to clipboard"),
        Err(e) => progress.print_warning(&format!("Failed to copy to clipboard: {}", e)),
    }
}
```

### Phase 7.5: Build and test
```bash
cargo build --release
cargo build

# Test clipboard functionality
./target/release/ipcrawler -t 127.0.0.1 --dry-run --copy-ports
./target/release/ipcrawler -t 127.0.0.1 --dry-run --copy-summary

# Verify clipboard contents (paste somewhere)
```

### Phase 7.6: Verification checklist
- [ ] arboard and lazy_static added
- [ ] Clipboard module compiles
- [ ] --copy-ports works
- [ ] --copy-summary works
- [ ] Graceful failure if clipboard unavailable
- [ ] Works on current OS

---

## 🚀 **PHASE 8: Smart File Opening**
*Open results in appropriate applications*

### 🚫 PHASE 8 ANTI-HARDCODING RULES:
- File opening logic must be based on file extensions, not tool names
- No hardcoded application associations for specific tools
- File type detection must be generic and work with any tool output format
- Application selection must be metadata-driven or system-default based

### Phase 8.0: Add open dependency
**File:** `Cargo.toml`
```toml
[dependencies]
# ... existing dependencies ...
open = "5.3"
```

### Phase 8.1: Add open commands
**File:** `src/cli.rs`
```rust
#[derive(Parser, Debug)]
pub struct Cli {
    // ... existing fields ...
    
    #[arg(long = "open-html", help = "Open HTML report in browser after scan")]
    pub open_html: bool,
    
    #[arg(long = "open-dir", help = "Open output directory in file manager after scan")]
    pub open_dir: bool,
}
```

### Phase 8.2: Integrate file opening
**File:** `src/main.rs`
```rust
// After saving reports:
if args.open_html {
    let html_path = output_dir.join("scan_summary.html");
    if html_path.exists() {
        match open::that(&html_path) {
            Ok(_) => progress.print_success("🌐 Opened HTML report in browser"),
            Err(e) => progress.print_warning(&format!("Failed to open HTML report: {}", e)),
        }
    }
}

if args.open_dir {
    match open::that(&output_dir) {
        Ok(_) => progress.print_success("📁 Opened output directory"),
        Err(e) => progress.print_warning(&format!("Failed to open directory: {}", e)),
    }
}
```

### Phase 8.3: Build and test
```bash
cargo build --release
cargo build

# Test file opening
./target/release/ipcrawler -t 127.0.0.1 --dry-run --open-html
./target/release/ipcrawler -t 127.0.0.1 --dry-run --open-dir
```

### Phase 8.4: Verification checklist
- [ ] open crate added
- [ ] --open-html opens browser
- [ ] --open-dir opens file manager
- [ ] Graceful failure if can't open
- [ ] Works on current OS

---

## 📊 **Final Integration Testing**

### Test all features together
```bash
# Full feature test
./target/release/ipcrawler \
    -t example.com \
    --verbose \
    --interactive \
    --notify \
    --copy-summary \
    --open-html \
    --dry-run

# TUI test (separate)
./target/release/ipcrawler -t example.com --tui
```

### Performance verification
```bash
# Measure binary size increase
ls -lh target/release/ipcrawler

# Check compilation time
time cargo build --release

# Memory usage comparison
/usr/bin/time -l ./target/release/ipcrawler -t 127.0.0.1 --dry-run
```

### Backward compatibility check
```bash
# Test all original commands still work
./target/release/ipcrawler --help
./target/release/ipcrawler --doctor
./target/release/ipcrawler --list
./target/release/ipcrawler --paths
./target/release/ipcrawler -t example.com -c default --dry-run
```

---

## 📚 **Documentation Updates Required**

After all phases complete:

1. Update README.md with new features
2. Update CLI help text with examples
3. Create docs/TUI_GUIDE.md for dashboard usage
4. Update docs/installation.md with new optional features
5. Add screenshots/GIFs of TUI dashboard
6. Update CHANGELOG.md with all changes

---

## 🎯 **Success Criteria**

- [ ] All phases build successfully
- [ ] No breaking changes to existing CLI
- [ ] TUI dashboard works smoothly
- [ ] Notifications appear on supported platforms
- [ ] Tables render correctly
- [ ] Interactive prompts enhance UX
- [ ] Clipboard integration works
- [ ] File opening works
- [ ] Performance impact < 20% for non-TUI mode
- [ ] Binary size increase < 50%

---

## 🚨 **Rollback Plan**

If issues arise:

1. **Feature flags**: Disable problematic features via Cargo.toml
2. **Git revert**: Each phase is a separate commit, easy to revert
3. **Conditional compilation**: Use `#[cfg(feature = "...")]` to exclude code
4. **Fallback modes**: All features have non-breaking fallbacks

---

## 📝 **Notes for AI Implementers**

1. **ALWAYS** run `cargo check` after every code change
2. **NEVER** remove or modify existing public APIs
3. **ALWAYS** use feature flags for new major features
4. **TEST** on at least one real target (even 127.0.0.1)
5. **STOP** at Phase 6 for human testing of TUI
6. **COMMIT** after each successful phase
7. **DOCUMENT** any deviations from this plan

---

## 🚫 **CRITICAL ANTI-HARDCODING ENFORCEMENT**

### The Golden Rules (MUST FOLLOW IN ALL PHASES):

1. **NO TOOL-SPECIFIC CODE**: Never write `if tool_name == "nmap"` or similar hardcoded checks
2. **YAML-DRIVEN LOGIC**: All tool information must come from YAML configuration files
3. **METADATA-BASED DECISIONS**: Use tool categories, types, and metadata instead of tool names
4. **GENERIC PATTERNS**: Write code that works with ANY tool defined in YAML
5. **DYNAMIC BEHAVIOR**: Tool detection, alternatives, and handling must be configuration-driven

### Enforcement Checklist (Check After Every Phase):
- [ ] No string literals matching specific tool names in match statements
- [ ] No hardcoded tool alternatives or suggestions
- [ ] No tool-specific formatting or parsing logic
- [ ] All tool behavior driven by YAML metadata
- [ ] Generic interfaces that work with any configured tool
- [ ] No assumptions about specific tool output formats
- [ ] Tool categorization based on metadata, not names

### Example VIOLATIONS to AVOID:
```rust
// ❌ BAD - Hardcoded tool names
match tool.name {
    "nmap" => handle_nmap_output(),
    "nikto" => handle_nikto_output(),
    _ => handle_generic_output()
}

// ❌ BAD - Hardcoded alternatives
let alternatives = vec!["nmap", "masscan", "rustscan"];

// ❌ BAD - Tool-specific parsing
if output.contains("Nmap scan report") {
    parse_nmap_output()
}
```

### Example CORRECT Patterns:
```rust
// ✅ GOOD - Metadata-driven behavior  
match tool.metadata.get("category") {
    Some("port_scanner") => handle_port_scanner_output(),
    Some("web_scanner") => handle_web_scanner_output(),
    _ => handle_generic_output()
}

// ✅ GOOD - Configuration-driven alternatives
let alternatives = tool.metadata
    .get("alternatives")
    .and_then(|v| v.as_array())
    .unwrap_or_default();

// ✅ GOOD - Generic parsing based on structure
if output.contains(&tool.metadata.get("success_indicator").unwrap_or("")) {
    parse_successful_output()
}
```

This plan is designed to be followed step-by-step by an AI coding assistant. Each phase builds on the previous one, with clear verification steps, rollback options, and strict anti-hardcoding enforcement.