# Rust Reconnaissance Tool - AI Development Phases

## Phase 1: Project Setup & Core CLI Structure

You are building a Rust-based reconnaissance automation tool. This is **PHASE 1 of 4**. Do NOT implement any other functionality beyond what's specified in this phase.

### PHASE 1 REQUIREMENTS:

1. **Create new Rust project** with proper Cargo.toml dependencies

2. **Implement basic CLI structure** using clap with these flags:
   - `--target/-t` (required): IP address or hostname
   - `--config/-c`: YAML config file path (default: config/default.yaml)
   - `--output/-o`: Output directory (default: results/)
   - `--debug/-d`: Enable debug mode
   - `--verbose/-v`: Verbose output
   - `--help/-h`: Help menu

3. **Add these dependencies** to Cargo.toml:
   ```toml
   clap = { version = "4.0", features = ["derive"] }
   tokio = { version = "1.0", features = ["full"] }
   serde = { version = "1.0", features = ["derive"] }
   serde_yaml = "0.9"
   chrono = { version = "0.4", features = ["serde"] }
   colored = "2.0"
   indicatif = "0.17"
   ```

4. **Create this folder structure:**
   ```
   src/
   ├── main.rs
   ├── cli.rs
   ├── config.rs (placeholder)
   ├── executor.rs (placeholder)
   └── output.rs (placeholder)
   config/
   └── default.yaml (empty for now)
   ```

5. **Implement colored terminal output** with proper formatting:
   - Success messages in green
   - Error messages in red
   - Info messages in blue
   - Warning messages in yellow
   - Progress indicators using indicatif

6. **Create output directory structure** on startup:
   ```
   results/{target}_{timestamp}/
   results/{target}_{timestamp}/logs/
   results/{target}_{timestamp}/raw/
   results/{target}_{timestamp}/errors/
   ```

### RULES:
- Use structured logging with timestamps
- Handle all `unwrap()` calls with proper error handling
- Make CLI help text clear and professional
- Timestamp format: `YYYY-MM-DD_HH-MM-SS`
- This is **PHASE 1 only** - do NOT implement YAML parsing, tool execution, or any other features
- Confirm completion and wait for PHASE 2 instructions

---

## Phase 2: YAML Configuration & Parsing

### PHASE 2 REQUIREMENTS - YAML Configuration System:

Implement YAML configuration parsing and validation. **Do NOT implement tool execution yet.**

1. **Define YAML schema** for config/default.yaml:
   ```yaml
   metadata:
     name: "Default Scan Profile"
     description: "Basic reconnaissance profile"
     version: "1.0"

   tools:
     - name: "nmap_quick"
       command: "nmap -sV -T4 {target} -oX {output}/raw/nmap_quick.xml"
       timeout: 300
       output_file: "nmap_quick.xml"
       enabled: true
       
     - name: "naabu"
       command: "naabu -host {target} -o {output}/raw/naabu_ports.txt"
       timeout: 60
       output_file: "naabu_ports.txt"
       enabled: true

   chains:
     - name: "port_to_service"
       from: "naabu"
       to: "nmap_quick"
       condition: "has_output"
       
   globals:
     max_concurrent: 3
     retry_count: 2
     log_level: "info"
   ```

2. **Implement config.rs** with:
   - Struct definitions for Config, Tool, Chain
   - YAML deserialization
   - Configuration validation
   - Template variable replacement (`{target}`, `{output}`)

3. **Add configuration loading** to main.rs
4. **Add `--validate` flag** to test config files
5. **Proper error handling** for malformed YAML

### RULES:
- Use serde for YAML parsing
- Validate all required fields
- Support config file includes/extends (basic)
- This is **PHASE 2 only** - wait for PHASE 3 before implementing execution

---

## Phase 3: Tool Execution Engine

### PHASE 3 REQUIREMENTS - Execution Engine:

Implement the core tool execution system. **Do NOT implement chaining yet.**

1. **Implement executor.rs** with:
   - Async tool execution using `tokio::process::Command`
   - Real-time output capture (stdout/stderr)
   - Timeout handling
   - Live log writing to separate files

2. **Output management:**
   - Raw tool output → `results/{target}_{timestamp}/raw/{tool_name}.out`
   - Tool errors → `results/{target}_{timestamp}/errors/{tool_name}.err`
   - Execution logs → `results/{target}_{timestamp}/logs/execution.log`

3. **Progress indicators:**
   - Per-tool progress bars
   - Overall scan progress
   - ETA calculations
   - Live status updates

4. **Tool execution features:**
   - Concurrent execution (respecting max_concurrent limit)
   - Graceful cancellation (Ctrl+C handling)
   - Resource monitoring (basic)
   - Retry logic for failed tools

5. **Logging system:**
   - Structured JSON logs for parsing
   - Human-readable console output
   - Debug mode with verbose tool output
   - Log rotation for large outputs

### RULES:
- Use tokio streams for real-time output
- Implement proper signal handling
- All file I/O must be async
- Add execution metrics (start time, duration, exit codes)
- This is **PHASE 3 only** - wait for PHASE 4 before implementing tool chaining

---

## Phase 4: Tool Chaining & Final Features

### PHASE 4 REQUIREMENTS - Advanced Features:

Complete the tool with chaining and polish features.

1. **Implement pipeline.rs:**
   - Tool dependency resolution
   - Output parsing and filtering
   - Chain execution logic
   - Data flow between tools

2. **Chain conditions:**
   - `"has_output"`: Check if previous tool produced output
   - `"exit_success"`: Check if previous tool exited successfully
   - `"contains"`: Check if output contains specific text
   - `"file_size"`: Check minimum output file size

3. **Result aggregation:**
   - Generate summary report (JSON + HTML)
   - Tool execution statistics
   - Failed tool reporting
   - Discovered services/ports summary

4. **Advanced CLI features:**
   - `--resume`: Resume interrupted scans
   - `--dry-run`: Show what would be executed
   - `--list-tools`: Show available tools from config
   - `--profile`: Quick profile selection

5. **Error handling & recovery:**
   - Graceful degradation when tools are missing
   - Automatic dependency checking
   - Recovery from partial failures
   - Tool installation suggestions

6. **Documentation:**
   - README with installation/usage
   - Example configurations
   - Tool integration guide
   - Troubleshooting section

### FINAL RULES:
- Add comprehensive error messages
- Include tool version checking
- Support custom tool definitions
- Add scan resumption capability
- Generate final scan report with all results
- Polish CLI UX with clear status messages

**This completes the full reconnaissance automation tool.**

---

## Key Features Summary

- **YAML-based configuration** for tools and chains
- **Concurrent tool execution** with progress tracking
- **Organized output structure** with separate logs/errors/raw data
- **Modern CLI** with colored output and progress bars
- **Tool chaining** based on conditions
- **Resumable scans** and error recovery
- **Real-time output capture** and live logging
- **Professional UX** with clear status messages

## Technical Stack

- **Language:** Rust
- **CLI Framework:** clap
- **Async Runtime:** tokio
- **Configuration:** serde_yaml
- **Terminal UI:** colored + indicatif
- **Logging:** chrono for timestamps