package runner

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"sync"
	"syscall"
	"time"

	"github.com/neur0map/ipcrawler/internal/config"
	"github.com/neur0map/ipcrawler/internal/wizard"
)

// JobStatus represents the current state of a tool execution.
type JobStatus int

const (
	StatusPending JobStatus = iota
	StatusWaiting
	StatusRunning
	StatusDone
	StatusFailed
	StatusSkipped
)

// Stream identifies the source of a line update.
type Stream int

const (
	StreamStdout Stream = iota
	StreamStderr
)

// JobUpdate is sent over the Updates channel to communicate state changes
// and live output to the display layer.
type JobUpdate struct {
	ToolName  string
	Status    JobStatus
	Line      string // stdout/stderr line, or dependency name for StatusWaiting
	Stream    Stream
	Err       error
	Duration  time.Duration
	WaitingOn string // dependency name when Status == StatusWaiting
}

// JobResult captures the final outcome of a tool execution.
type JobResult struct {
	ToolName string
	Status   JobStatus
	Duration time.Duration
	Err      error
}

// job is an internal representation of a single tool to execute.
type job struct {
	template config.Template
	command  string
}

// Runner manages concurrent execution of tools via a worker pool.
type Runner struct {
	jobs      []job
	workers   int
	outputDir string
	logFile   *os.File
	Updates   chan JobUpdate
	results   []JobResult
	mu        sync.Mutex
}

// New creates a Runner from a validated RunConfig.
// Tools are expected to already be sorted by priority.
func New(cfg *wizard.RunConfig) *Runner {
	jobs := make([]job, len(cfg.Tools))
	for i, t := range cfg.Tools {
		jobs[i] = job{
			template: t,
			command:  cfg.Commands[t.Name],
		}
	}
	return &Runner{
		jobs:      jobs,
		workers:   cfg.Workers,
		outputDir: cfg.OutputDir,
		Updates:   make(chan JobUpdate, 500),
	}
}

// Results returns a copy of the collected job results after execution.
func (r *Runner) Results() []JobResult {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]JobResult, len(r.results))
	copy(out, r.results)
	return out
}

func (r *Runner) recordResult(name string, status JobStatus, duration time.Duration, err error) {
	r.mu.Lock()
	r.results = append(r.results, JobResult{
		ToolName: name,
		Status:   status,
		Duration: duration,
		Err:      err,
	})
	r.mu.Unlock()
}

// Execute runs all jobs concurrently, bounded by the worker pool size.
// Jobs are dispatched in priority order. Dependencies are respected:
// a tool with depends_on blocks until all named dependencies finish successfully.
// If a dependency failed or wasn't selected, the dependent tool is skipped.
func (r *Runner) Execute(ctx context.Context) {
	defer close(r.Updates)

	// Open engine log
	logPath := filepath.Join(r.outputDir, "logs", "engine.log")
	if f, err := os.Create(logPath); err == nil {
		r.logFile = f
		defer func() { _ = f.Close() }()
	}

	// Sort jobs by priority (lowest first = earliest wave)
	sort.SliceStable(r.jobs, func(i, j int) bool {
		return r.jobs[i].template.Priority < r.jobs[j].template.Priority
	})

	r.log("ipcrawler engine started — %d jobs, %d workers", len(r.jobs), r.workers)

	// Completion tracking for dependencies:
	// - completion[name] is closed when a tool finishes (success, fail, or skip)
	// - finalStatus[name] records the terminal status for dependency checks
	completion := make(map[string]chan struct{})
	finalStatus := make(map[string]JobStatus)
	var statusMu sync.Mutex

	for _, j := range r.jobs {
		completion[j.template.Name] = make(chan struct{})
	}

	var wg sync.WaitGroup
	sem := make(chan struct{}, r.workers)

	for _, j := range r.jobs {
		wg.Add(1)
		go func(j job) {
			defer wg.Done()
			name := j.template.Name

			// Signal completion when this goroutine exits, regardless of outcome
			defer func() {
				close(completion[name])
			}()

			// Wait for all dependencies before acquiring a worker slot
			if !r.waitForDeps(ctx, j, completion, finalStatus, &statusMu) {
				return // skipped or context cancelled
			}

			// Acquire worker slot
			select {
			case sem <- struct{}{}:
			case <-ctx.Done():
				return
			}
			defer func() { <-sem }()

			status := r.runJob(ctx, j)

			statusMu.Lock()
			finalStatus[name] = status
			statusMu.Unlock()
		}(j)
	}

	wg.Wait()
	r.log("all jobs complete")
}

// waitForDeps blocks until all dependencies of j have completed successfully.
// Returns true if all deps are satisfied and execution should proceed.
// Returns false if a dep failed/missing (tool is skipped) or context cancelled.
func (r *Runner) waitForDeps(
	ctx context.Context,
	j job,
	completion map[string]chan struct{},
	finalStatus map[string]JobStatus,
	statusMu *sync.Mutex,
) bool {
	name := j.template.Name

	for _, dep := range j.template.DependsOn {
		depCh, exists := completion[dep]
		if !exists {
			// Dependency wasn't selected — treat as satisfied so the
			// tool can still run. This lets Hosts Updater work when
			// only some recon tools are picked.
			r.log("dep-skip: %s → dependency %q not selected, treating as satisfied", name, dep)
			continue
		}

		// Notify tracker we're waiting on this dependency
		r.send(JobUpdate{ToolName: name, Status: StatusWaiting, WaitingOn: dep})
		r.log("waiting: %s → dependency %q", name, dep)

		// Block until dep finishes or context is cancelled
		select {
		case <-depCh:
			statusMu.Lock()
			depResult := finalStatus[dep]
			statusMu.Unlock()

			if depResult != StatusDone {
				reason := fmt.Errorf("skipped: dependency %q failed", dep)
				r.log("skipped: %s — %v", name, reason)
				r.send(JobUpdate{ToolName: name, Status: StatusSkipped, Err: reason})
				r.recordResult(name, StatusSkipped, 0, reason)

				statusMu.Lock()
				finalStatus[name] = StatusSkipped
				statusMu.Unlock()
				return false
			}
		case <-ctx.Done():
			return false
		}
	}

	return true
}

// runJob executes a single tool, capturing stdout/stderr to files
// and sending live updates over the channel. Returns the terminal status.
func (r *Runner) runJob(ctx context.Context, j job) JobStatus {
	name := j.template.Name
	start := time.Now()

	r.send(JobUpdate{ToolName: name, Status: StatusRunning})
	r.log("started: %s → %s", name, j.command)

	// Create timeout context from template config
	timeout := j.template.TimeoutDuration()
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// Do NOT use CommandContext — it only kills the parent process.
	// We manage cancellation ourselves via process group kill.
	cmd := exec.Command("sh", "-c", j.command)
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		r.fail(name, start, fmt.Errorf("stdout pipe: %w", err))
		return StatusFailed
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		r.fail(name, start, fmt.Errorf("stderr pipe: %w", err))
		return StatusFailed
	}

	// Open output files
	rawPath := filepath.Join(r.outputDir, "raw", config.SanitizeName(name)+".txt")
	errPath := filepath.Join(r.outputDir, "errors", config.SanitizeName(name)+"_err.txt")

	rawFile, err := os.Create(rawPath)
	if err != nil {
		r.fail(name, start, fmt.Errorf("create raw file: %w", err))
		return StatusFailed
	}
	defer func() { _ = rawFile.Close() }()

	errFile, err := os.Create(errPath)
	if err != nil {
		r.fail(name, start, fmt.Errorf("create error file: %w", err))
		return StatusFailed
	}
	defer func() { _ = errFile.Close() }()

	// Start the process
	if err := cmd.Start(); err != nil {
		r.fail(name, start, fmt.Errorf("start: %w", err))
		return StatusFailed
	}

	// Read pipes concurrently — must complete before cmd.Wait()
	var pipeWg sync.WaitGroup
	pipeWg.Add(2)

	// Stdout reader: write to file + send live updates
	go func() {
		defer pipeWg.Done()
		scanner := bufio.NewScanner(stdout)
		scanner.Buffer(make([]byte, 256*1024), 256*1024) // 256KB line buffer
		for scanner.Scan() {
			line := scanner.Text()
			_, _ = rawFile.WriteString(line + "\n")
			// Non-blocking send for line updates to avoid stalling the tool
			r.trySend(JobUpdate{ToolName: name, Status: StatusRunning, Line: line, Stream: StreamStdout})
		}
	}()

	// Stderr reader: write to file + send live updates
	go func() {
		defer pipeWg.Done()
		scanner := bufio.NewScanner(stderr)
		scanner.Buffer(make([]byte, 256*1024), 256*1024)
		for scanner.Scan() {
			line := scanner.Text()
			_, _ = errFile.WriteString(line + "\n")
			r.trySend(JobUpdate{ToolName: name, Status: StatusRunning, Line: line, Stream: StreamStderr})
		}
	}()

	// Monitor context in a goroutine — kill the entire process group
	// (parent + all children) if the timeout or cancellation fires.
	doneCh := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			if cmd.Process != nil {
				pgid := cmd.Process.Pid
				r.log("killing process group %d for %s: %v", pgid, name, ctx.Err())
				_ = syscall.Kill(-pgid, syscall.SIGKILL)
			}
		case <-doneCh:
			// Process exited normally, nothing to kill.
		}
	}()

	// Wait for pipes to drain, then wait for process exit
	pipeWg.Wait()
	cmdErr := cmd.Wait()
	close(doneCh) // signal the kill goroutine to stop
	duration := time.Since(start)

	if ctx.Err() != nil {
		// Context expired — treat as a timeout/cancellation failure
		err := fmt.Errorf("killed: %w", ctx.Err())
		r.log("failed: %s (%s) — %v", name, duration.Round(time.Millisecond), err)
		r.send(JobUpdate{ToolName: name, Status: StatusFailed, Err: err, Duration: duration})
		r.recordResult(name, StatusFailed, duration, err)
		return StatusFailed
	} else if cmdErr != nil {
		r.log("failed: %s (%s) — %v", name, duration.Round(time.Millisecond), cmdErr)
		r.send(JobUpdate{ToolName: name, Status: StatusFailed, Err: cmdErr, Duration: duration})
		r.recordResult(name, StatusFailed, duration, cmdErr)
		return StatusFailed
	}

	r.log("completed: %s (%s)", name, duration.Round(time.Millisecond))
	r.send(JobUpdate{ToolName: name, Status: StatusDone, Duration: duration})
	r.recordResult(name, StatusDone, duration, nil)
	return StatusDone
}

// send performs a blocking send for critical status updates.
func (r *Runner) send(update JobUpdate) {
	r.Updates <- update
}

// trySend performs a non-blocking send for line updates.
// If the channel is full, the update is dropped — raw output is
// always persisted to files regardless.
func (r *Runner) trySend(update JobUpdate) {
	select {
	case r.Updates <- update:
	default:
	}
}

// fail sends a failed status and logs the error.
func (r *Runner) fail(name string, start time.Time, err error) {
	duration := time.Since(start)
	r.log("failed: %s — %v", name, err)
	r.send(JobUpdate{ToolName: name, Status: StatusFailed, Err: err, Duration: duration})
	r.recordResult(name, StatusFailed, duration, err)
}

// log writes a timestamped message to the engine log file.
func (r *Runner) log(format string, args ...interface{}) {
	if r.logFile == nil {
		return
	}
	msg := fmt.Sprintf(format, args...)
	ts := time.Now().Format("15:04:05.000")
	_, _ = fmt.Fprintf(r.logFile, "[%s] %s\n", ts, msg)
}
