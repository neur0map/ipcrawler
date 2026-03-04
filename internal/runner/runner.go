package runner

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"

	"github.com/neur0map/ipcrawler/internal/config"
	"github.com/neur0map/ipcrawler/internal/wizard"
)

// JobStatus represents the current state of a tool execution.
type JobStatus int

const (
	StatusPending JobStatus = iota
	StatusRunning
	StatusDone
	StatusFailed
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
	ToolName string
	Status   JobStatus
	Line     string
	Stream   Stream
	Err      error
	Duration time.Duration
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
// It closes the Updates channel when all jobs are complete.
func (r *Runner) Execute(ctx context.Context) {
	defer close(r.Updates)

	// Open engine log
	logPath := filepath.Join(r.outputDir, "logs", "engine.log")
	if f, err := os.Create(logPath); err == nil {
		r.logFile = f
		defer f.Close()
	}

	r.log("ipcrawler engine started — %d jobs, %d workers", len(r.jobs), r.workers)

	var wg sync.WaitGroup
	sem := make(chan struct{}, r.workers)

	for _, j := range r.jobs {
		wg.Add(1)
		go func(j job) {
			defer wg.Done()
			sem <- struct{}{}        // acquire worker slot
			defer func() { <-sem }() // release worker slot
			r.runJob(ctx, j)
		}(j)
	}

	wg.Wait()
	r.log("all jobs complete")
}

// runJob executes a single tool, capturing stdout/stderr to files
// and sending live updates over the channel.
func (r *Runner) runJob(ctx context.Context, j job) {
	name := j.template.Name
	start := time.Now()

	r.send(JobUpdate{ToolName: name, Status: StatusRunning})
	r.log("started: %s → %s", name, j.command)

	// Create timeout context from template config
	timeout := j.template.TimeoutDuration()
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "sh", "-c", j.command)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		r.fail(name, start, fmt.Errorf("stdout pipe: %w", err))
		return
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		r.fail(name, start, fmt.Errorf("stderr pipe: %w", err))
		return
	}

	// Open output files
	rawPath := filepath.Join(r.outputDir, "raw", config.SanitizeName(name)+".txt")
	errPath := filepath.Join(r.outputDir, "errors", config.SanitizeName(name)+"_err.txt")

	rawFile, err := os.Create(rawPath)
	if err != nil {
		r.fail(name, start, fmt.Errorf("create raw file: %w", err))
		return
	}
	defer rawFile.Close()

	errFile, err := os.Create(errPath)
	if err != nil {
		r.fail(name, start, fmt.Errorf("create error file: %w", err))
		return
	}
	defer errFile.Close()

	// Start the process
	if err := cmd.Start(); err != nil {
		r.fail(name, start, fmt.Errorf("start: %w", err))
		return
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
			rawFile.WriteString(line + "\n")
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
			errFile.WriteString(line + "\n")
			r.trySend(JobUpdate{ToolName: name, Status: StatusRunning, Line: line, Stream: StreamStderr})
		}
	}()

	// Wait for pipes to drain, then wait for process exit
	pipeWg.Wait()
	cmdErr := cmd.Wait()
	duration := time.Since(start)

	if cmdErr != nil {
		r.log("failed: %s (%s) — %v", name, duration.Round(time.Millisecond), cmdErr)
		r.send(JobUpdate{ToolName: name, Status: StatusFailed, Err: cmdErr, Duration: duration})
		r.recordResult(name, StatusFailed, duration, cmdErr)
	} else {
		r.log("completed: %s (%s)", name, duration.Round(time.Millisecond))
		r.send(JobUpdate{ToolName: name, Status: StatusDone, Duration: duration})
		r.recordResult(name, StatusDone, duration, nil)
	}
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
	fmt.Fprintf(r.logFile, "[%s] %s\n", ts, msg)
}
