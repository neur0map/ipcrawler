Rust Reconnaissance Tool - Phase 1 & 2 Implementation Record

  Project Overview

  Built a Rust-based reconnaissance automation tool with YAML configuration support, colored CLI output, and structured project organization.

  Phase 1: Project Setup & Core CLI Structure

  1.1 Project Initialization

  - Project Name: rust_recon_tool
  - Rust Edition: 2024 (latest stable edition as of February 2025)
  - Base Directory: /Users/carlosm/Documents/ipcrawler-rust/

  1.2 Dependencies Added (Cargo.toml)

  [package]
  name = "rust_recon_tool"
  version = "0.1.0"
  edition = "2024"

  [dependencies]
  clap = { version = "4.0", features = ["derive"] }
  tokio = { version = "1.0", features = ["full"] }
  serde = { version = "1.0", features = ["derive"] }
  serde_yaml = "0.9"
  chrono = { version = "0.4", features = ["serde"] }
  colored = "2.0"
  indicatif = "0.17"

  1.3 File Structure Created

  ipcrawler-rust/
  ├── Cargo.toml
  ├── Cargo.lock
  ├── config/
  │   └── default.yaml
  ├── src/
  │   ├── main.rs        # Main entry point with colored output
  │   ├── cli.rs         # CLI argument parsing with clap
  │   ├── config.rs      # YAML configuration (placeholder in Phase 1)
  │   ├── executor.rs    # Tool execution (placeholder in Phase 1)
  │   └── output.rs      # Output management (placeholder in Phase 1)
  └── results/           # Created at runtime

  1.4 CLI Implementation (src/cli.rs)

  Implemented CLI flags using clap with derive macros:
  - --target/-t (required): IP address or hostname
  - --config/-c: YAML config file path (default: config/default.yaml)
  - --output/-o: Output directory (default: results/)
  - --debug/-d: Enable debug mode
  - --verbose/-v: Verbose output
  - --help/-h: Help menu (automatic via clap)

  1.5 Main Application Features (src/main.rs)

  Colored Terminal Output

  Implemented color-coded messages using the colored crate:
  - Success messages: Green (✓ prefix)
  - Error messages: Red (✗ prefix)
  - Info messages: Blue (ℹ prefix)
  - Warning messages: Yellow (⚠ prefix)

  Helper functions created:
  fn print_success(msg: &str)  // Green output
  fn print_error(msg: &str)    // Red output to stderr
  fn print_info(msg: &str)     // Blue output
  fn print_warning(msg: &str)  // Yellow output
  fn timestamp() -> String     // YYYY-MM-DD HH:MM:SS format

  Progress Indicators

  Used indicatif crate for visual progress bars:
  - Animated spinner with green color
  - Progress bar with cyan/blue gradient
  - Elapsed time display
  - Status messages during initialization

  Output Directory Structure

  Created automatic directory structure on startup:
  results/{target}_{timestamp}/
  ├── logs/
  │   └── execution.log    # Timestamped execution logs
  ├── raw/                 # Raw tool output (Phase 3)
  └── errors/              # Error logs (Phase 3)

  Format: results/192_168_1_1_2025-08-20_22-04-17/

  1.6 Error Handling

  - All functions return Result<T, Box<dyn std::error::Error>>
  - No unwrap() calls - proper error propagation with ? operator
  - Structured logging with timestamps to execution.log

  1.7 Phase 1 Testing

  Successfully tested:
  - CLI help output: cargo run -- --help
  - Basic execution: cargo run -- --target 192.168.1.1 --debug --verbose
  - Directory creation verified with proper structure
  - Log file creation with timestamped entries

  Phase 2: YAML Configuration & Parsing

  2.1 YAML Schema Definition (config/default.yaml)

  Created comprehensive YAML structure:
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

  2.2 Configuration Structures (src/config.rs)

  Data Structures

  Implemented Serde-compatible structs:
  #[derive(Debug, Deserialize, Serialize, Clone)]
  pub struct Config {
      pub metadata: Metadata,
      pub tools: Vec<Tool>,
      pub chains: Vec<Chain>,
      pub globals: Globals,
  }

  pub struct Metadata { name, description, version }
  pub struct Tool { name, command, timeout, output_file, enabled }
  pub struct Chain { name, from, to, condition }
  pub struct Globals { max_concurrent, retry_count, log_level }

  Key Methods Implemented

  Config::from_file(path: &Path):
  - Reads YAML file from disk
  - Deserializes using serde_yaml
  - Automatically validates configuration
  - Returns Result with proper error handling

  Config::validate():
  Comprehensive validation including:
  - Metadata field validation (non-empty name, version)
  - Tool validation:
    - Non-empty names and commands
    - Timeout > 0
    - At least one tool must exist
  - Chain validation:
    - References to existing tools
    - Valid conditions: has_output, exit_success, contains, file_size
  - Global settings validation:
    - max_concurrent > 0
    - Valid log levels: trace, debug, info, warn, error

  Config::replace_variables():
  Template variable replacement system:
  - Replaces {target} with actual target IP/hostname
  - Replaces {output} with actual output directory path
  - Applied to both commands and output_file fields

  Config::print_summary():
  Beautiful colored configuration summary showing:
  - Profile metadata
  - Tools with enabled status (✓/✗)
  - Chain relationships with arrows
  - Global settings

  2.3 CLI Enhancement

  Modified src/cli.rs to add:
  - --validate flag for configuration testing
  - Made target optional (required unless --validate is present)
  - Used required_unless_present attribute for conditional requirements

  2.4 Main.rs Integration

  Updated main function with:
  1. Configuration Loading:
    - Load config file at startup
    - Display success/error messages
    - Handle validation mode separately
  2. Validate Mode:
    - When --validate flag is set:
    - Validates configuration
    - Prints summary
    - Exits without creating directories or running tools
  3. Normal Mode:
    - Loads and validates configuration
    - Creates output directories
    - Replaces template variables
    - Shows progress bars
    - Displays configuration summary in verbose mode

  2.5 Phase 2 Testing

  Successful Tests

  1. Valid Configuration:
  cargo run -- --validate
  # Output: Configuration loaded, validated, and summary displayed
  2. With Target:
  cargo run -- --target 10.0.0.1 --verbose
  # Output: Configuration loaded, variables replaced, directories created

  Error Handling Tests

  1. Invalid Configuration (empty metadata name):
  cargo run -- --validate --config config/invalid.yaml
  # Error: "Config metadata name cannot be empty"
  2. Invalid Chain Reference:
  cargo run -- --validate --config config/invalid_chain.yaml
  # Error: "Chain 'broken_chain' references non-existent tool 'nonexistent_tool'"

  2.6 Key Implementation Details

  Fixed Issues During Development

  1. Rust Edition: Initially set to 2021, corrected to 2024 after verifying it was stabilized in Rust 1.85.0 (February 2025)
  2. Variable Shadowing: Fixed timestamp variable shadowing function name by renaming to dir_timestamp
  3. Unused Import: Removed unused self import from std::io
  4. Target Handling: Made target optional for validation mode using Option<String>

  Color Scheme Established

  - Cyan: Headers and configuration summaries
  - Blue: Information messages
  - Green: Success indicators and enabled tools
  - Yellow: Warnings and chain relationships
  - Red: Errors and disabled tools
  - Magenta: Global settings

  Technical Achievements

  Phase 1 Accomplishments

  ✅ Rust project with modern 2024 edition✅ Complete CLI with all required flags✅ Colored terminal output with status prefixes✅ Progress bars with animations✅
  Structured output directories with timestamps✅ Proper error handling without unwrap()✅ Logging system with timestamped entries

  Phase 2 Accomplishments

  ✅ YAML configuration schema defined✅ Serde-based deserialization✅ Comprehensive validation system✅ Template variable replacement ({target}, {output})✅
  Configuration summary display✅ --validate flag for testing configs✅ Error messages for invalid configurations✅ Integration with Phase 1 infrastructure

  File Sizes & Complexity

  - main.rs: 134 lines (with complete Phase 2 integration)
  - cli.rs: 27 lines (with validation flag)
  - config.rs: 144 lines (full validation and parsing)
  - Total new code: ~305 lines of functional Rust code

  Ready for Phase 3

  The foundation is now complete with:
  - CLI argument parsing
  - Configuration management
  - Output directory structure
  - Colored terminal interface
  - Progress tracking
  - Error handling framework

  Phase 3 will add the actual tool execution engine using the tokio async runtime.