# Architecture Documentation

## System Overview

IPCrawler is built as a modular, asynchronous Rust application designed for parallel security tool execution with a focus on extensibility and type safety.

## Module Structure

```
src/
├── main.rs                # Entry point & orchestration with LLM integration
├── cli.rs                 # CLI parsing, port/target parsing, dry-run & verbose modes
├── config/
│   ├── mod.rs            # Module exports
│   ├── schema.rs         # YAML schema definitions
│   └── wordlist.rs       # Wordlist configuration
├── system/
│   ├── mod.rs            # Module exports
│   ├── detect.rs         # OS, package manager, sudo detection
│   └── script_security.rs # Script validation and sandboxing
├── tools/
│   ├── mod.rs            # Module exports
│   ├── registry.rs       # Tool discovery & loading
│   └── installer.rs      # Tool installation
├── executor/
│   ├── mod.rs            # Module exports
│   ├── queue.rs          # Task queue management
│   └── runner.rs         # Parallel task execution with script support
├── llm/
│   ├── mod.rs            # LLM module exports
│   ├── client.rs         # LLM client for OpenAI/Claude/Ollama
│   └── prompts.rs        # Prompt templates and security analysis
├── output/
│   ├── mod.rs            # Module exports
│   ├── parser.rs         # Enhanced output parsing with LLM support
│   ├── universal.rs      # Universal Output Parser with ContentAnalyzer
│   └── reporter.rs       # Enhanced report generation with narratives
└── ui/
    ├── mod.rs            # Module exports
    ├── cli.rs            # CLI interface components
    └── tui.rs            # Terminal UI (ratatui)
```

## Key Components

### CLI Module (`cli.rs`)

**Responsibilities:**
- Command-line argument parsing using clap
- Target parsing (IP, CIDR, file-based)
- Port parsing (lists, ranges, modes)
- Input validation
- LLM configuration options
- Dry-run and verbose mode support

**Key Functions:**
- `parse_targets()` - Converts input to IP list
- `parse_ports()` - Converts input to port list
- `parse_port_mode()` - Maps port modes to nmap flags

**New CLI Options:**
- `--use-llm` - Enable LLM-powered analysis
- `--llm-provider` - Choose LLM provider (openai/claude/ollama)
- `--llm-api-key` - API key for LLM service
- `--llm-model` - Custom LLM model
- `--llm-base-url` - Custom LLM endpoint
- `--dry-run` - Test parsing without execution
- `--verbose` - Detailed output with alternative parsing

**Port Modes:**
- `fast` → nmap `-F`
- `top-1000` → nmap `--top-ports 1000`
- `all` → nmap `-p-`
- Custom lists/ranges

### Config Module (`config/`)

**Responsibilities:**
- YAML schema definitions
- Tool configuration loading
- Wordlist configuration management
- Command template rendering

**Key Types:**
- `Tool` - Represents a security tool
- `OutputConfig` - Defines output parsing
- `Pattern` - Regex pattern for findings
- `WordlistConfig` - Wordlist paths

**Template System:**
- Uses Handlebars for command rendering
- Supports placeholders: `{{target}}`, `{{port}}`, `{{output_file}}`, `{{wordlist}}`
- Dynamic command selection based on sudo status

### System Module (`system/`)

**Responsibilities:**
- Operating system detection
- Package manager detection
- Sudo/root privilege detection
- Shell script security validation

**Key Functions:**
- `detect_os()` - Identifies OS (Linux, macOS, Windows)
- `detect_package_manager()` - Finds available package manager
- `is_running_as_root()` - Checks for elevated privileges
- `ScriptSecurity::validate_script()` - Validates shell scripts

**Security Features:**
- Dangerous command blocking
- Suspicious pattern detection
- File size limits
- Automatic executable permissions

### Tools Module (`tools/`)

**Responsibilities:**
- Tool discovery from YAML files
- Tool registry management
- Missing tool installation

**Key Components:**
- `ToolRegistry` - Loads and manages tools
- `ToolInstaller` - Handles tool installation
- YAML discovery in `tools/` directory

**Installation Flow:**
1. Check if tool binary exists
2. If missing, offer installation
3. Detect package manager
4. Execute installer command
5. Verify installation

### Executor Module (`executor/`)

**Responsibilities:**
- Task queue management
- Parallel task execution
- Timeout handling
- Script preparation and validation

**Key Components:**
- `TaskQueue` - FIFO queue for tasks
- `TaskRunner` - Async execution engine
- `Task` - Represents a single tool execution

**Execution Model:**
- Tokio-based async runtime
- Semaphore limiting (max 5 concurrent)
- Timeout per task
- Real-time status updates via channels

**Task Lifecycle:**
1. Queued
2. Running (semaphore acquired)
3. Completed/Failed/TimedOut
4. Results collected

### LLM Module (`llm/`)

**Responsibilities:**
- LLM client abstraction for multiple providers
- Security-focused prompt templates
- Context-aware analysis
- Template-based output analysis

**Key Components:**
- `LLMClient` - Unified client for OpenAI/Claude/Ollama
- `PromptTemplate` - Customizable prompt templates
- `SecurityAnalysisPrompt` - Specialized security analysis prompts
- `Message` - Conversation context management

**Features:**
- Multi-provider support (OpenAI, Claude, Ollama)
- Template-based analysis
- Context-aware conversations
- Connection testing and validation

### Output Module (`output/`)

**Responsibilities:**
- Enhanced output parsing with LLM integration
- Universal Output Parser with ContentAnalyzer
- Deduplicate findings with advanced algorithms
- Generate reports with narratives and insights
- Save individual tool logs

**Key Components:**
- `OutputParser` - Enhanced parser with LLM support
- `UniversalProcessor` - LLM-powered content analysis
- `ContentAnalyzer` - Specialized analysis methods
- `ReportGenerator` - Enhanced report generation
- Finding deduplication with fuzzy matching
- Severity-based sorting with LLM assessment

**Parsing Methods:**
- `parse()` - Original parsing with optional LLM
- `parse_sync()` - Synchronous parsing for dry-run
- `parse_with_llm()` - Full LLM-powered analysis
- `analyze_with_llm()` - LLM-only analysis

**Output Types:**
- `json` - Structured JSON findings parsing (recommended)
- `regex` - Pattern matching with regex (traditional tools)
- `xml` - XML parsing (legacy support)
- LLM enhancement - Natural language analysis (optional)

**JSON Parsing Architecture:**

```
Shell Script Output
│
├─> stdout: JSON findings
│   └─> Parsed by UniversalProcessor::parse_json_findings()
│       └─> Creates Finding objects from JSON array
│
├─> stderr with markers: Raw tool output
│   └─> Extracted by extract_marked_content()
│       ├─> Between ===START_RAW_OUTPUT=== and ===END_RAW_OUTPUT===
│       └─> Sent to LLM for analysis (if enabled)
│
└─> Complete output: Saved to logs/
    └─> Full stdout + stderr in logs/{tool}_{target}_{port}.log
```

**JSON Findings Schema:**
```json
{
  "findings": [
    {
      "severity": "info|low|medium|high|critical",
      "title": "Finding title",
      "description": "Detailed description",
      "port": 80  // Optional
    }
  ],
  "metadata": {}  // Optional, preserved but not parsed
}
```

**Marker-Based Extraction:**
- Markers separate raw tool output from JSON findings
- Raw output between markers sent to LLM for AI analysis
- Enables both structured parsing AND intelligent analysis
- Complete output always preserved in logs/

### UI Module (`ui/`)

**Responsibilities:**
- Terminal user interface
- Real-time progress display
- Vulnerability feed
- Task status visualization

**Key Features:**
- Header panel (scan info, progress)
- Execution table (tool status)
- Findings feed (live updates)
- Colored severity indicators

## Execution Flow

### 1. Initialization Phase

```
main.rs
  ├─> Load environment variables (.env support)
  ├─> Parse CLI arguments (including LLM options)
  ├─> Detect sudo privileges
  ├─> Load wordlist configuration
  ├─> Create LLM client (if enabled)
  ├─> Test LLM connection and templates
  ├─> Parse targets and ports
  └─> Create output directory (target_HHMM format)
```

### 2. Tool Discovery Phase

```
main.rs
  ├─> Load ToolRegistry
  ├─> Discover YAML files in tools/
  ├─> Parse tool configurations
  └─> Validate tool schemas
```

### 3. Tool Installation Phase

```
main.rs
  ├─> Create ToolInstaller
  ├─> Check each tool installation
  │   ├─> Tool exists? → Continue
  │   └─> Tool missing? → Offer installation
  └─> Wait for all installations
```

### 4. Task Generation Phase

```
main.rs
  ├─> For each tool:
  │   ├─> For each target:
  │   │   ├─> Check if tool needs ports
  │   │   ├─> For each port (if needed):
  │   │   │   ├─> Select command (sudo vs normal)
  │   │   │   ├─> Render command template
  │   │   │   ├─> Resolve wordlist
  │   │   │   └─> Create Task
  │   │   └─> Add to TaskQueue
  └─> Total task count
```

### 5. Execution Phase

```
TaskRunner
  ├─> Create semaphore (limit 5)
  ├─> Spawn tasks concurrently
  │   ├─> Acquire semaphore
  │   ├─> Validate script (if .sh)
  │   ├─> Execute command
  │   ├─> Capture stdout/stderr
  │   ├─> Handle timeout
  │   └─> Release semaphore
  ├─> Update UI in real-time
  └─> Collect results
```

### 6. Processing Phase

```
main.rs
  ├─> Parse each result (method based on mode)
  │   ├─> Verbose mode: Original parse() with LLM option
  │   ├─> Normal mode: Enhanced parse_with_llm()
  │   ├─> Dry-run mode: Synchronous parse_sync()
  │   ├─> Match output patterns (regex/json/xml)
  │   ├─> LLM analysis (if enabled)
  │   ├─> Extract findings with context
  │   └─> Assign severity with LLM assessment
  ├─> Advanced deduplication (fuzzy matching)
  ├─> Sort by severity with LLM priority
  └─> Return enhanced findings list
```

### 7. Reporting Phase

```
ReportGenerator
  ├─> Generate enhanced Markdown report
  │   ├─> Scan metadata with LLM insights
  │   ├─> Discovery narratives
  │   ├─> Services analysis sections
  │   ├─> Enhanced vulnerability lists
  │   └─> Execution log with LLM context
  ├─> Generate JSON report
  │   ├─> Structured findings with LLM analysis
  │   └─> Machine-readable with enhanced metadata
  └─> Save individual logs
```

## Data Flow

```
CLI Input
  ↓
Target/Port Parsing
  ↓
Tool Discovery & Loading
  ↓
Task Generation (Tool × Target × Port)
  ↓
Parallel Execution (max 5 concurrent)
  ↓
Output Capture (stdout/stderr)
  ↓
Pattern Matching (regex/json/xml)
  ↓
Finding Extraction
  ↓
Deduplication & Sorting
  ↓
Report Generation (MD + JSON)
  ↓
File System Output
```

## Concurrency Model

### Async Runtime
- Tokio for asynchronous I/O
- Multi-threaded work-stealing scheduler
- Efficient resource utilization

### Concurrency Limits
- Maximum 5 concurrent tasks
- Implemented via `Arc<Semaphore>`
- Prevents resource exhaustion

### Communication
- Channels for status updates
- `mpsc::unbounded_channel` for UI updates
- `Arc<Mutex<HashMap>>` for shared state

## Error Handling

### Strategy
- `anyhow::Result` for error propagation
- Context-rich error messages
- Graceful degradation

### Tool Failures
- Individual tool failures don't stop scan
- Errors logged and reported
- Continue with remaining tasks

### User Feedback
- Real-time error display
- Detailed error messages in logs
- Actionable error suggestions

## Security Architecture

### Defense in Depth

**Layer 1: Script Validation**
- Static analysis of shell scripts
- Pattern matching for dangerous commands
- Rejection before execution

**Layer 2: Process Isolation**
- Each tool runs in separate process
- Limited by timeout
- No shared state

**Layer 3: Filesystem Restrictions**
- Output to designated directory only
- No arbitrary file writes
- Temporary files cleaned up

**Layer 4: Privilege Management**
- Explicit sudo detection
- Separate commands for privileged mode
- No automatic privilege escalation

## Performance Optimization

### Parallel Execution
- Up to 5 tools run simultaneously
- Maximizes CPU and network utilization
- Semaphore prevents overload

### Efficient Parsing
- Streaming parsers for large outputs
- Regex compilation cached
- JSON/XML native parsing

### Memory Management
- Rust's ownership model prevents leaks
- Results collected incrementally
- Large outputs streamed to disk

## Extensibility Points

### Adding New Tools
1. Create YAML in `tools/`
2. Define command template
3. Specify output patterns
4. No code changes required

### Custom Parsers
- Implement pattern matching
- Support JSON, XML, regex
- Extensible via YAML

### Custom Scripts
- Place in `tools/scripts/`
- Reference in YAML
- Automatic validation

### Output Formats
- New reporters can be added
- Implement `ReportGenerator` trait
- Support additional formats

## Dependencies

### Core Dependencies
- `tokio` - Async runtime
- `clap` - CLI parsing
- `serde` - Serialization
- `anyhow` - Error handling

### LLM Dependencies
- `reqwest` - HTTP client for LLM APIs
- `dotenvy` - Environment variable loading
- `handlebars` - Prompt template rendering

### UI Dependencies
- `ratatui` - Terminal UI
- `crossterm` - Terminal control
- `colored` - Color output

### Parsing Dependencies
- `regex` - Pattern matching
- `serde_json` - JSON parsing
- `serde_yaml` - YAML parsing

### Utility Dependencies
- `handlebars` - Template rendering
- `ipnetwork` - CIDR parsing
- `chrono` - Timestamp handling
- `libc` - System calls (sudo detection)
