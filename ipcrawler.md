# ipcrawler — Build & Architecture Guide (v0.1.0-alpha)

> ## THINK MODE (MANDATORY)
> You are an expert Rust developer. Before any code:
> 1. **Inspect** the repo tree (or absence of one) and all scripts.
> 2. **Plan** in phases (Phase 1 → 1.1 → 1.2 …) with explicit success criteria.
> 3. **Justify** design choices (trade-offs, error handling, UX).
> 4. **Verify** with web search and **Context7 MCP** for docs/manpages when integrating tools or crates.
> If something isn’t verified, treat it as unknown until you check.

---

## Project Intent (short + blunt)
`ipcrawler` is a simple, modern CLI that orchestrates external recon tools via a typed, compile-time plugin model and a strict, bounded-concurrency scheduler. Everything is **dev-local** (binaries, outputs, logs, helper scripts). User-facing output must be consistent and derived from a single in-memory truth—never hardcoded. The run **fails fast** with precise provenance; **reports are mandatory** (missing/invalid reports = failed run).

---

## Non-Negotiable Rules
- **Dev-only containment**: all binaries, artifacts, outputs, logs, and tool paths live **inside this repo folder**. No system installs. No global `$PATH` writes.
- **Minimal CLI**: only `-t|--target <STR>`, `-v|--verbose`, `-d|--debug`, `-h|--help`. Nothing else.
- **NEVER HARDCODE USER-FACING RESULTS**: all counts (ports, services, tasks) come from the central state object.
- **NEVER HARDCODE SCANS OR FALLBACKS**: if a tool or step fails/missing, **halt** with a precise error (tool, args, exit code, stderr tail). No silent substitutions.
- **Reports & organizers MUST always work**: report write + validate are part of success; failure here fails the run.
- **`main.rs` is entry-point only**: no business logic there. Keep modules clean and single-purpose.
- **UI correctness over flair**: modern but restrained output; no duplicated/conflicting numbers; no drift.

---

## Repository Layout (from an empty folder)
ipcrawler/
├─ Cargo.toml
├─ Makefile
├─ .gitignore
├─ README.md
├─ scripts/
│  ├─ install_tools.sh       # Manual/explicit tool setup (optional).
│  ├─ check_tools.sh         # Verifies presence/versions; exits non-zero if missing.
│  ├─ run.sh                 # Stable runner; forwards args to local binary.
│  └─ env.sh                 # Optional env (e.g., RUST_LOG) sourced by scripts.
├─ artifacts/
│  ├─ bin/                   # Built binaries (dev-only; copied here after cargo build).
│  ├─ runs/                  # Per-run outputs (timestamped).
│  └─ logs/                  # Human + JSON logs.
└─ src/
├─ main.rs                # Entry only: parse CLI, init logs, call app::run().
├─ app.rs                 # App bootstrapping/wiring.
├─ cli/
│  └─ args.rs             # Minimal CLI flags and parsing.
├─ core/
│  ├─ models.rs           # Target, Service, RunDirs, RunId…
│  ├─ errors.rs           # Error types (rich provenance).
│  ├─ events.rs           # Event enums for consistent state updates.
│  ├─ state.rs            # Authoritative in-memory state (RunState).
│  └─ scheduler.rs        # Bounded concurrency, cancellation, DAG execution.
├─ ui/
│  ├─ printer.rs          # All user-facing rendering reads RunState only.
│  └─ progress.rs         # Indicatif MultiProgress spinners/bars (restrained).
├─ executors/
│  ├─ command.rs          # Tokio process wrapper, streaming, timeouts, tee-to-log.
│  ├─ toolchain.rs        # Local tool discovery/validation (no fallbacks).
│  └─ runners.rs          # Higher-level “run X” helpers (optional).
├─ organizers/
│  ├─ layout.rs           # Per-run tree creation, fsync for durability.
│  └─ audit.rs            # Preflight: writability, disk space, path sanity.
├─ plugins/
│  ├─ mod.rs              # Static registry of compiled-in plugins.
│  ├─ types.rs            # Traits: PortScan, ServiceScan, Report.
│  ├─ portscan_nmap.rs    # Example: nmap → Vec.
│  └─ http_probe.rs       # Example: curl/httpx probe.
├─ reporters/
│  ├─ writer.rs           # summary.txt/json (atomic writes).
│  └─ validate.rs         # Verify report presence & integrity.
└─ utils/
├─ fs.rs               # Atomic writes, safe file IO.
├─ time.rs             # Run IDs, timestamps.
└─ logging.rs          # tracing setup (human + JSON).


---

## Cargo.toml (lean + modern baseline)

```toml
[package]
name = "ipcrawler"
version = "0.1.0-alpha"
edition = "2024"

[dependencies]
# CLI + serde
clap = { version = "4", features = ["derive"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Async + process handling
tokio = { version = "1", features = ["full"] }
tokio-util = "0.7"

# Output & UX
indicatif = "0.17"
console = "0.15"
yansi = "1"

# Logging & errors
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "fmt", "json"] }
thiserror = "1"
anyhow = "1"

# Helpers
regex = "1"
quick-xml = "0.36"
async-trait = "0.1"
which = "6"

```
Makefile
Makefile (fast dev cycles)

Note: make interprets leading -v, -d etc. as its own flags.
Use one of:
	•	make run RUN_ARGS="-v -t example.com" (recommended), or
	•	make run -- -v -t example.com (GNU make passthrough).
    # Makefile — dev-only; all artifacts in ./artifacts
```

```makefile
BIN_DIR      := artifacts/bin
BIN          := $(BIN_DIR)/ipcrawler
LOG_DIR      := artifacts/logs
RUN_DIR      := artifacts/runs
PROFILE      ?= release
RUN_ARGS     ?=

.PHONY: help build run clean fmt clippy check tools verify

help:
	@echo "Targets:"
	@echo "  make build                        - Build $(BIN) (dev-only)"
	@echo "  make run RUN_ARGS=\"-v -t host\"     - Run with args"
	@echo "  make tools                        - Install/verify external tools locally"
	@echo "  make verify                       - Verify env and folder writability"
	@echo "  make fmt | make clippy | check    - Format, lint, tests"

build:
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR)
	@cargo build --$(PROFILE)
	@cp -f target/$(PROFILE)/ipcrawler $(BIN)
	@echo "Built $(BIN)"

run: build
	@./scripts/run.sh $(RUN_ARGS)

tools:
	@bash scripts/install_tools.sh

verify:
	@bash scripts/check_tools.sh
	@mkdir -p $(RUN_DIR) $(LOG_DIR) && touch $(LOG_DIR)/.write && rm $(LOG_DIR)/.write
	@echo "Environment verified."

fmt:
	cargo fmt --all

clippy:
	cargo clippy -- -D warnings

check:
	cargo test

# Swallow incidental phony goals if user passes flags directly
%:
	@:
```
scripts/scripts/
run.sh
```
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/artifacts/bin/ipcrawler"

if [[ ! -x "$BIN" ]]; then
  echo "Binary not found at $BIN. Run 'make build' first." >&2
  exit 1
fi

export RUST_LOG="${RUST_LOG:-info}"

exec "$BIN" "$@"
```
scripts/scripts/
check_tools.sh
```
#!/usr/bin/env bash
set -euo pipefail

ok()  { printf "✔ %s\n" "$1"; }
bad() { printf "✘ %s\n" "$1"; }

missing=0

need() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 $( "$1" --version 2>&1 | head -n1 )"
  else
    bad "$1 not found"
    missing=1
  fi
}

echo "Checking external tools..."
need nmap
need curl

if [[ $missing -ne 0 ]]; then
  echo "fatal: missing dependencies. Run: make tools" >&2
  exit 1
fi
```
install_tools.sh
```
#!/usr/bin/env bash
set -euo pipefail

# Intentionally minimal: no auto-installs, no hidden steps.
echo "Nothing to install by default."
echo "Install dependencies via your package manager, then run: make verify"
```

---

## CLI (src/cli/args.rs)

```rust
// Purpose: minimal CLI parsing. Only -t, -v, -d, -h.
// Key: no hidden flags; debug implies verbose.
// Guarantees: target is required; defaults explicit.

use clap::{Parser, ArgAction};

#[derive(Parser, Debug, Clone)]
#[command(name = "ipcrawler", version, author = "ipcrawler")]
pub struct Cli {
    /// Target host/IP/domain to scan (required)
    #[arg(short = 't', long = "target")]
    pub target: String,

    /// Verbose human output
    #[arg(short = 'v', long = "verbose", action = ArgAction::SetTrue)]
    pub verbose: bool,

    /// Debug logs (implies verbose)
    #[arg(short = 'd', long = "debug", action = ArgAction::SetTrue)]
    pub debug: bool,
}

```
Entry point: src/main.rs
```
// Purpose: entry only. Parse CLI, init logging, call app::run().

mod app;
mod cli;

use clap::Parser;

fn main() {
    let cli = cli::args::Cli::parse();
    if let Err(err) = app::run(cli) {
        eprintln!("fatal: {:#}", err);
        std::process::exit(1);
    }
}
```

src/app.rs
```
// Purpose: wire logging, layout, tool checks, then invoke scheduler and reporters.

use crate::{
    core::{state::RunState, models::Target},
    organizers::layout,
    executors::toolchain,
    reporters::{writer, validate},
    utils::{logging, time},
    plugins,
};

pub fn run(cli: crate::cli::args::Cli) -> anyhow::Result<()> {
    let level = logging::level_from_cli(&cli);
    logging::init(level)?;
    let run_id = time::new_run_id();

    let dirs = layout::prepare_run_dirs(&run_id)?;
    toolchain::verify_or_bail()?; // No fallbacks. Precise error on missing deps.

    let target = Target::new(cli.target.clone(), run_id.clone(), dirs.clone())?;
    let mut state = RunState::new(&target, &dirs);

    // Execute: port-scan → service-scans; bounded concurrency; fail-fast.
    crate::core::scheduler::execute_all(&mut state, &plugins::REGISTRY)?;

    // Reports must succeed or run is considered failed.
    writer::write_all(&state, &dirs)?;
    validate::validate_reports(&dirs)?;

    Ok(())
}
```

---

## Core Modules

### `src/core/models.rs`

```rust
// Purpose: domain types (Target, Service, RunDirs, Proto).
// Guarantees: pure data, no business logic.

use std::path::PathBuf;

#[derive(Clone)]
pub struct RunDirs {
    pub root: PathBuf,    // artifacts/runs/<id>
    pub scans: PathBuf,
    pub loot: PathBuf,
    pub report: PathBuf,
    pub logs: PathBuf,
}

#[derive(Clone)]
pub struct Target {
    pub value: String,    // host/IP/domain
    pub run_id: String,
    pub dirs: RunDirs,
}

#[derive(Clone)]
pub enum Proto { Tcp, Udp }

#[derive(Clone)]
pub struct Service {
    pub proto: Proto,
    pub port: u16,
    pub name: String,     // e.g., "http", "ssh"
    pub secure: bool,     // e.g., https
    pub address: String,  // normalized host/IP
}

impl Target {
    pub fn new(value: String, run_id: String, dirs: RunDirs) -> anyhow::Result<Self> {
        Ok(Self { value, run_id, dirs })
    }
}
```
src/core/events.rs
```
// Purpose: event types for consistent RunState updates.

use super::models::Service;
use super::errors::ExecError;

pub enum Event {
    TaskStarted(&'static str),   // plugin/task name
    TaskCompleted(&'static str),
    PortDiscovered(u16, String), // port, service name
    ServiceDiscovered(Service),
    TaskFailed(ExecError),
}
```
src/core/state.rs
```
// Purpose: single source of truth for user-facing data.
// Guarantees: UI only reads from here; prevents drift.

use super::{events::Event, models::{Service, Target}};
use crate::core::errors::ExecError;

pub struct RunState {
    pub target: Target,
    pub ports_open: Vec<(u16, String)>,
    pub services: Vec<Service>,
    pub tasks_started: usize,
    pub tasks_completed: usize,
    pub errors: Vec<ExecError>,
}

impl RunState {
    pub fn new(target: &Target, _dirs: &crate::core::models::RunDirs) -> Self {
        Self {
            target: target.clone(),
            ports_open: vec![],
            services: vec![],
            tasks_started: 0,
            tasks_completed: 0,
            errors: vec![],
        }
    }

    pub fn on_event(&mut self, ev: Event) {
        match ev {
            Event::TaskStarted(_) => self.tasks_started += 1,
            Event::TaskCompleted(_) => self.tasks_completed += 1,
            Event::PortDiscovered(p, n) => self.ports_open.push((p, n)),
            Event::ServiceDiscovered(s) => self.services.push(s),
            Event::TaskFailed(e) => self.errors.push(e),
        }
    }
}
```
src/core/errors.rs
```
// Purpose: rich errors with precise provenance for fail-fast behavior.

use thiserror::Error;

#[derive(Debug, Clone)]
pub struct ExecError {
    pub tool: String,
    pub args: Vec<String>,
    pub cwd: String,
    pub exit_code: Option<i32>,
    pub stderr_tail: String,
    pub duration_ms: u128,
}

#[derive(Error, Debug)]
pub enum IpcrawlerError {
    #[error("execution failed: {0:?}")]
    Exec(ExecError),
    #[error("report failure: {0}")]
    Report(String),
    #[error("organizer failure: {0}")]
    Organizer(String),
    #[error("dependency missing: {0}")]
    Dependency(String),
}
```
src/core/scheduler.rs
```
// Purpose: orchestrate plugin execution with strict caps + fail-fast cancellation.
// Guarantees: concurrency bounded, errors stop the run, state always updated.

use std::sync::Arc;
use tokio::sync::Semaphore;
use crate::plugins::{REGISTRY, PortScan, ServiceScan};
use super::{state::RunState, events::Event, models::Service};

pub async fn execute_all_async(state: &mut RunState, registry: &REGISTRY) -> anyhow::Result<()> {
    let max_scans: usize = 50;  // total (service + port)
    let max_ports: usize = 10;  // reserved for port scans (~20%)
    let sem_ports = Arc::new(Semaphore::new(max_ports));
    let sem_svcs  = Arc::new(Semaphore::new(max_scans - max_ports));

    // Port scans
    let mut discovered: Vec<Service> = vec![];
    for p in &registry.port_scans {
        let _permit = sem_ports.acquire().await?;
        state.on_event(Event::TaskStarted(p.name()));
        match p.run(&state.target, state).await {
            Ok(mut svcs) => {
                discovered.append(&mut svcs);
                state.on_event(Event::TaskCompleted(p.name()));
            }
            Err(e) => return Err(e),
        }
    }

    // Service scans
    for s in discovered.iter() {
        for plg in &registry.service_scans {
            if !plg.matches(s) { continue; }
            let _permit = sem_svcs.acquire().await?;
            state.on_event(Event::TaskStarted(plg.name()));
            if let Err(e) = plg.run(s, state).await {
                return Err(e);
            }
            state.on_event(Event::TaskCompleted(plg.name()));
        }
    }

    Ok(())
}

pub fn execute_all(state: &mut RunState, registry: &REGISTRY) -> anyhow::Result<()> {
    tokio::runtime::Runtime::new()?.block_on(execute_all_async(state, registry))
}
```

# ipcrawler — Remaining Documentation (Prompt Style, No Code)

> You are in **THINK MODE**. You are an expert Rust dev. Skeptical by default. Verify assumptions with docs/Context7 before committing to behavior.

Below are detailed prompts/specs for the remaining components. **Do not** invent silent fallbacks. **Do** fail fast with precise provenance. **All user-facing counts must originate from `RunState`**.

---

## Executors

### `src/executors/command.rs` — Process Execution Contract
- **Purpose**: Provide a single, consistent way to run external commands and capture their outputs with rich error context. This is the only path by which tools (nmap, curl, etc.) are executed.
- **Inputs**: Full command line string; working directory (`RunDirs.scans` or another run subdir); optional file paths for output/err; optional timeout.
- **Outputs**: 
  - On success: captured stdout/stderr (or confirmations that they were written to files), duration, and exit code.
  - On failure: a structured error object containing tool, full args, working directory, exit code (if any), last N lines of stderr, and duration.
- **Behavior**:
  - Stream stdout/stderr incrementally to avoid large-buffer stalls. Tee to files if requested.
  - Enforce timeouts where applicable; timeouts are treated as failures (include elapsed duration).
  - Normalize line endings and ensure file outputs are flushed and fsync’d when appropriate.
  - Do not guess encodings—assume UTF-8, but tolerate non-UTF-8 by lossily decoding only for logs; persist raw bytes to output files when needed.
- **Invariants**:
  - **No hidden fallbacks**: never swap binaries or lower flags automatically.
  - **Deterministic error reporting**: always include the exact command, directory, and exit code.
- **Observability**:
  - Emit tracing events for start/end with durations and exit status.
  - Redact potentially sensitive values (if any appear in args) based on a safe-list/redaction policy.
- **Testing**:
  - Success: run a benign command, assert outputs and duration > 0.
  - Failure: invoke a non-existent option, assert exit code, stderr tail present.
  - Timeout: simulate a long-running command, assert timeout error shape.

---

### `src/executors/toolchain.rs` — Dependency Verification
- **Purpose**: Validate that required external tools are available **before** the scheduler starts.
- **Inputs**: List of required tools (initially `nmap`, `curl`).
- **Outputs**: Either success (all present) or a single clear error naming the missing tool(s) with user instructions.
- **Behavior**:
  - Look up tools via a deterministic method (system PATH lookup or repo-local path if you add that later).
  - Do not attempt to install; instruct the user to run `make tools` or install manually.
- **Invariants**:
  - If any tool is missing, **abort** early. No partial scans allowed.
- **Testing**:
  - Pass: all tools present.
  - Fail: remove/rename one tool, assert precise message.

---

## Organizers

### `src/organizers/layout.rs` — Run Directory Structure
- **Purpose**: Create the per-run directory tree and ensure it is durable (fsync where supported).
- **Inputs**: `run_id` and repo-relative `artifacts/` base.
- **Outputs**: A `RunDirs` object with absolute paths to `root`, `scans`, `loot`, `report`, `logs`.
- **Behavior**:
  - Create directories if missing. If any directory creation fails, return an error with path and OS message.
  - On Unix, fsync directory handles to reduce risk of metadata loss.
  - Ensure paths are normalized and writable; preflight with a touch/remove test in `artifacts/logs/`.
- **Invariants**:
  - Never write outside the project folder.
  - Every downstream module must only use paths provided by `RunDirs`.
- **Testing**:
  - Normal: dirs created, write test passes.
  - Permission-denied: simulate unwritable dir, assert error.

---

### `src/organizers/audit.rs` — Environment Preflight
- **Purpose**: Pre-run checks that catch predictable failures early.
- **Inputs**: `RunDirs`, free disk space threshold, OS limits (e.g., file descriptors on Unix).
- **Outputs**: Success or a single error summarizing all issues found (aggregate errors).
- **Behavior**:
  - Verify free space ≥ threshold.
  - (Optional) Check `ulimit -n` on Unix and warn/fail if too low for the configured concurrency.
  - Validate expected write permissions across all `RunDirs`.
- **Invariants**:
  - Must not mutate global OS state; only report.
- **Testing**:
  - Normal: everything passes.
  - Low space / permission issue: assert consolidated error message lists each failed check.

---

## Reporters

### `src/reporters/writer.rs` — Summary Output (Atomic)
- **Purpose**: Persist human-readable and JSON summaries of the run. These are **required** outputs.
- **Inputs**: Final `RunState`, `RunDirs`.
- **Outputs**: `report/summary.txt` and `report/summary.json`, written **atomically** (temp file + rename), with durable flush.
- **Behavior**:
  - Human summary must include: target, open ports count, discovered services count, tasks completed/started, and errors count. **All numbers read from `RunState` only.**
  - JSON summary mirrors the human data and should be schema-stable for downstream tooling.
  - If any write fails, return an error immediately (the run fails).
- **Invariants**:
  - No partial files: atomic writes only.
  - No derived counts outside `RunState`.
- **Testing**:
  - Normal: files exist and are non-empty.
  - Failure: simulate write permission error; assert error.

### `src/reporters/validate.rs` — Post-Write Integrity
- **Purpose**: Provide a final gate that ensures required report files exist and are non-empty.
- **Inputs**: `RunDirs`.
- **Outputs**: Success or a clear error specifying which file is missing/empty.
- **Behavior**:
  - Check presence and non-zero size of required files.
  - Optionally validate JSON structure for sanity (schema presence).
- **Invariants**:
  - If validation fails, the entire run is considered failed.
- **Testing**:
  - Normal: both files valid.
  - Missing/empty: assert targeted error.

---

## UI Layer

### `src/ui/progress.rs` — Progress Feedback (Restrained)
- **Purpose**: User-facing progress indicators that are modern but not noisy. Must never misreport counts.
- **Inputs**: Task start/complete events; optional per-task short messages (tool name, target, port).
- **Outputs**: Ephemeral progress lines/spinners; final line is a compact summary.
- **Behavior**:
  - Keep a small, fixed number of visible lines; aggregate the rest to avoid terminal thrash.
  - Update messages only from event data; never compute new counts locally.
  - Avoid wrapping or truncation that hides critical info (tool name, port, result).
- **Invariants**:
  - No derived totals in this module. Pull display values from `RunState` or event payload.
- **Testing**:
  - Simulate bursts of tasks; ensure UI remains legible and consistent.

### `src/ui/printer.rs` — Final Summary (Consistent)
- **Purpose**: Produce the final concise summary to stdout after the run completes.
- **Inputs**: Final `RunState`.
- **Outputs**: One or two lines summarizing target, counts (ports/services/tasks/errors).
- **Behavior**:
  - Use consistent formatting and ordering across runs.
  - No extra narratives or guesses; keep to facts available in `RunState`.
- **Invariants**:
  - No hardcoded numbers, no re-counting. Only `RunState`.
- **Testing**:
  - Validate string contains the exact counts from `RunState`.

---

## Plugins System

### `src/plugins/types.rs` — Plugin Contracts
- **Purpose**: Define the trait contracts for `PortScan`, `ServiceScan`, and `Report`.
- **Scope**:
  - `PortScan` takes a `Target` and returns a list of discovered `Service`s.
  - `ServiceScan` matches specific `Service`s and enriches the dataset (e.g., HTTP probing).
  - `Report` (optional at this stage) can generate extra artifacts using final `RunState`.
- **Behavior**:
  - Every plugin must return precise errors on failure; never swallow.
  - `ServiceScan.matches` must be a pure predicate; no side effects.
- **Invariants**:
  - All plugin implementations use `executors::command` for process calls (no bypass).
  - No plugin writes UI output directly; they emit events/state changes only.

### `src/plugins/mod.rs` — Static Registry
- **Purpose**: Central place to list which plugins are compiled in and their order/priority.
- **Behavior**:
  - Provide deterministic ordering. If priority ties occur, use file-defined order.
  - No filesystem scanning; registry is static (compile-time choice).
- **Invariants**:
  - Only modules listed here are considered; no dynamic loading.
- **Testing**:
  - Ensure the registry contains expected plugin instances and order.

### `src/plugins/portscan_nmap.rs` — Port Discovery (Nmap)
- **Purpose**: Run Nmap in a discovery mode and convert results into `Service` objects.
- **Inputs**: `Target`, `RunDirs`.
- **Outputs**: A list of `Service` objects with protocol, port, service name, security flag, normalized address.
- **Behavior**:
  - Execute Nmap with safe, high-signal defaults for discovery. Stream output to file(s).
  - Parse results via XML or robust regex. For every open port, emit a `PortDiscovered` and `ServiceDiscovered`.
  - If Nmap exits non-zero, return a precise failure. Do not “retry” with different flags automatically.
- **Invariants**:
  - Never claim a port/service unless parsed from tool output.
  - All emitted counts must be reflected in `RunState`.
- **Testing**:
  - Simulated outputs for multiple ports/services.
  - Failure: bad flags or missing tool → precise error.

### `src/plugins/http_probe.rs` — HTTP/HTTPS Probe
- **Purpose**: For services with HTTP(S), fetch headers and minimal body to characterize the service.
- **Inputs**: `Service` with protocol, port, and security flag.
- **Outputs**: Files capturing response headers and the first part of the body; updates in `RunState` if you track per-service findings.
- **Behavior**:
  - Build URL from `Service` (never guess port/scheme inconsistently with the discovery).
  - Respect timeouts; capture response code and key headers; write artifacts to `scans/`.
  - On failure (timeout, TLS error), return a precise error; no fallbacks or retries unless explicitly scheduled elsewhere.
- **Invariants**:
  - This plugin runs **only if** a matching `Service` exists (no speculative requests).
  - Output filenames must be deterministic and derived from service attributes.
- **Testing**:
  - Local HTTP server with known response; assert artifacts exist.
  - TLS failure path returns a clear error.

---

## Utilities

### `src/utils/logging.rs` — Tracing Setup
- **Purpose**: Configure logging levels and format (human and machine).
- **Inputs**: CLI verbosity (`-v`, `-d`) mapped to `warn`/`info`/`debug`.
- **Outputs**: Initialized subscriber(s) for console output; file logs are handled at the application level (if added).
- **Behavior**:
  - Avoid double-initialization; fail if setup is attempted twice.
  - Use compact human output for terminals; JSON for structured logs if you wire file writers.
- **Invariants**:
  - Respect CLI flags; no hidden overrides.
- **Testing**:
  - Verify messages appear at the correct levels under `-v` and `-d`.

### `src/utils/time.rs` — Run IDs & Timestamps
- **Purpose**: Provide stable, filesystem-safe run IDs and human-readable timestamps.
- **Behavior**:
  - RFC3339-ish run ID with characters safe for directory names.
  - No collisions expected in practice; include seconds and a small entropy component if needed.

### `src/utils/fs.rs` — Atomic Writes
- **Purpose**: Helpers for atomic file operations.
- **Behavior**:
  - Write to `*.tmp`, then rename to the final path.
  - Ensure parent directories exist; bubble errors up precisely.
- **Testing**:
  - Simulate write failures; assert no partial files remain.

---

## Testing & Quality Gates

- **Formatting/Lint**: `cargo fmt --all` and `cargo clippy -D warnings` must pass on every build.
- **Unit Focus**:
  - `RunState` event handling correctness (no double counting, correct mutations).
  - `command` error shapes: exit code present, stderr tail captured, duration measured.
  - `writer` atomicity and `validate` required-file checks.
- **Smoke Test**:
  - Bring up a tiny local HTTP server; run the pipeline; assert summaries exist and counts match `RunState`.
- **Negative Tests**:
  - Missing `nmap` or `curl` → immediate failure with precise message.
  - Directory unwritable → `layout` or `writer` returns clear error; run fails.

---

## Scheduler Policies (Reiterated)

- **Two pools**: small reserved pool for port scans (≈20% of total), larger pool for service scans.
- **Fail-fast**: any plugin failure aborts the run; do not continue with downstream tasks.
- **No speculative work**: service scans only run for discovered services.
- **Backpressure**: do not spawn beyond semaphore limits; never leak tasks when errors occur.
- **Determinism**: plugins run in stable priority order.

---

## Phase Plan (from empty folder)

1. **Skeleton & Tooling**: repo layout, Cargo manifest, Makefile, scripts; compile “hello”.
2. **Core State & Logging**: implement `RunState`, events, logging init; a no-op scheduler that prints a stub summary.
3. **Executors & Toolchain**: process runner with rich errors; dependency verification.
4. **Scheduler**: bounded concurrency; fail-fast semantics; port-scan path returning an empty set initially.
5. **Plugins**: `portscan_nmap` (real parsing), `http_probe` (restricted probe).
6. **Reports**: writer (atomic) + validator; wire to success criteria.
7. **UI**: restrained progress; final summary that exactly mirrors `RunState`.
8. **Hardening**: tests, error messaging polish, docs review.

---

## Guardrails (repeat out loud)

- **Do not** print counts that you didn’t read from `RunState`.  
- **Do not** silently “try another tool” or “retry with different flags”.  
- **Do not** let report writing/validation fail silently—if that breaks, the run fails.  
- **Do not** bypass the scheduler when starting work.  
- **Do** surface exact tool names, arguments, CWD, exit codes, and stderr tails in failures.  
- **Do** keep all artifacts inside the repo’s `artifacts/` tree.

---

## Quickstart (Operator)

- `make verify`  
- `make run RUN_ARGS="-t scanme.nmap.org -v"`  
  (or `make run -- -t scanme.nmap.org -v` on GNU make)

Outputs live under `./artifacts/`. Logs under `./artifacts/logs/`. Reports under each run’s `report/`.

---

## Context7 MCP & Web Search (for you, the AI coder)

- Before integrating/changing tools, query **Context7 MCP** for official docs (Nmap flags, curl options, XML schemas).
- If any flag or behavior is unclear, pause and verify. No guessing. Document the source you used for decisions.

---