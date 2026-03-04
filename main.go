package main

import (
	"context"
	"embed"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/neur0map/ipcrawler/internal/config"
	"github.com/neur0map/ipcrawler/internal/report"
	"github.com/neur0map/ipcrawler/internal/runner"
	"github.com/neur0map/ipcrawler/internal/tracker"
	"github.com/neur0map/ipcrawler/internal/wizard"
)

//go:embed templates/*.yaml
var templateFS embed.FS

// --- Home Depot Orange palette ---

var (
	orange = lipgloss.Color("#F96302")
	white  = lipgloss.Color("#FFFFFF")
	cyan   = lipgloss.Color("#00FFFF")

	bannerStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(orange)

	successBox = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(orange).
			Padding(1, 2).
			MarginTop(1)

	successLabel = lipgloss.NewStyle().
			Foreground(white).
			Bold(true).
			Width(10)

	successValue = lipgloss.NewStyle().
			Foreground(cyan)
)

func main() {
	fmt.Println(bannerStyle.Render("\n  ipcrawler v0.1.0 — Security Tool Orchestrator\n"))

	templates, err := config.ParseTemplates(templateFS)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading templates: %v\n", err)
		os.Exit(1)
	}

	runCfg, err := wizard.Run(templates)
	if err != nil {
		fmt.Println("\n  Aborted.")
		os.Exit(0)
	}

	for _, d := range []string{"raw", "errors", "logs"} {
		if err := os.MkdirAll(filepath.Join(runCfg.OutputDir, d), 0755); err != nil {
			fmt.Fprintf(os.Stderr, "Error creating directories: %v\n", err)
			os.Exit(1)
		}
	}

	// --- Execute ---

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	r := runner.New(runCfg)

	done := make(chan struct{})
	go func() {
		r.Execute(ctx)
		close(done)
	}()

	toolNames := make([]string, len(runCfg.Tools))
	for i, t := range runCfg.Tools {
		toolNames[i] = t.Name
	}

	if runCfg.Verbose {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, os.Interrupt)
		go func() {
			<-sigCh
			cancel()
		}()
		tracker.RunVerbose(r.Updates)
	} else {
		m := tracker.NewModel(r.Updates, toolNames, cancel)
		p := tea.NewProgram(m)
		finalModel, _ := p.Run()

		if fm, ok := finalModel.(tracker.Model); ok && !fm.IsDone() {
			go func() {
				for range r.Updates {
				}
			}()
		}
	}

	cancel()
	<-done

	// --- Report ---

	if err := report.Compile(runCfg.OutputDir, buildReportData(runCfg, r.Results())); err != nil {
		fmt.Fprintf(os.Stderr, "Error compiling report: %v\n", err)
	}

	fmt.Println(renderSummary(runCfg))
}

func buildReportData(cfg *wizard.RunConfig, results []runner.JobResult) report.ReportData {
	resultMap := make(map[string]runner.JobResult, len(results))
	for _, res := range results {
		resultMap[res.ToolName] = res
	}

	toolResults := make([]report.ToolResult, 0, len(cfg.Tools))
	for _, t := range cfg.Tools {
		res := resultMap[t.Name]
		safeName := config.SanitizeName(t.Name)

		raw, _ := os.ReadFile(filepath.Join(cfg.OutputDir, "raw", safeName+".txt"))
		errData, _ := os.ReadFile(filepath.Join(cfg.OutputDir, "errors", safeName+"_err.txt"))

		status := "Success"
		failed := false
		if res.Status == runner.StatusFailed {
			status = "Failed"
			failed = true
		}

		toolResults = append(toolResults, report.ToolResult{
			Name:        t.Name,
			Category:    strings.ToUpper(t.Category),
			Description: t.Description,
			Command:     cfg.Commands[t.Name],
			Status:      status,
			Duration:    fmtDuration(res.Duration),
			Output:      strings.TrimRight(string(raw), "\n"),
			Stderr:      strings.TrimRight(string(errData), "\n"),
			Failed:      failed,
		})
	}

	return report.ReportData{
		Target:  cfg.Target,
		Date:    time.Now().Format("2006-01-02 15:04:05"),
		Results: toolResults,
	}
}

func fmtDuration(d time.Duration) string {
	if d < time.Second {
		return fmt.Sprintf("%dms", d.Milliseconds())
	}
	return fmt.Sprintf("%.1fs", d.Seconds())
}

func renderSummary(cfg *wizard.RunConfig) string {
	content := fmt.Sprintf(
		"%s  %s\n%s  %s\n%s  %s\n%s  %s",
		successLabel.Render("Status:"),
		successValue.Render("Complete"),
		successLabel.Render("Report:"),
		successValue.Render(filepath.Join(cfg.OutputDir, "report.md")),
		successLabel.Render("Raw:"),
		successValue.Render(filepath.Join(cfg.OutputDir, "raw/")),
		successLabel.Render("Logs:"),
		successValue.Render(filepath.Join(cfg.OutputDir, "logs/")),
	)
	return successBox.Render(content)
}
