package main

import (
	"context"
	"embed"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"sort"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/lipgloss"
	"github.com/neur0map/ipcrawler/internal/config"
	"github.com/neur0map/ipcrawler/internal/report"
	"github.com/neur0map/ipcrawler/internal/runner"
	"github.com/neur0map/ipcrawler/internal/tracker"
	"github.com/neur0map/ipcrawler/internal/wizard"
)

//go:embed templates/*/*.yaml
var templateFS embed.FS

// --- Home Depot Orange palette ---

var (
	orange = lipgloss.Color("#F96302")

	bannerStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(orange)

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

	// Sort tools by priority (lowest first) so both runner and tracker
	// see the same execution-wave order.
	sort.SliceStable(runCfg.Tools, func(i, j int) bool {
		return runCfg.Tools[i].Priority < runCfg.Tools[j].Priority
	})

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

	reportData := buildReportData(runCfg, r.Results())
	if err := report.Compile(runCfg.OutputDir, reportData); err != nil {
		fmt.Fprintf(os.Stderr, "Error compiling report: %v\n", err)
	}

	// Render the report to terminal via glamour
	reportPath := filepath.Join(runCfg.OutputDir, "report.md")
	if md, err := os.ReadFile(reportPath); err == nil {
		renderer, _ := glamour.NewTermRenderer(
			glamour.WithStylePath("dark"),
			glamour.WithWordWrap(0),
		)
		if rendered, err := renderer.Render(string(md)); err == nil {
			fmt.Print(rendered)
		}
	}

	// Final save prompt
	savePrompt := lipgloss.NewStyle().
		Foreground(orange).
		Bold(true).
		Padding(0, 1).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(orange)
	fmt.Println(savePrompt.Render("Report saved to " + reportPath))
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

		// Determine status string
		status := "Success"
		failed := false
		switch res.Status {
		case runner.StatusFailed:
			status = "Failed"
			failed = true
		case runner.StatusSkipped:
			status = "Skipped"
			failed = true
		}

		// Skipped tools have no output files — just record the skip reason
		if res.Status == runner.StatusSkipped {
			errMsg := ""
			if res.Err != nil {
				errMsg = res.Err.Error()
			}
			toolResults = append(toolResults, report.ToolResult{
				Name:        t.Name,
				Category:    strings.ToUpper(t.Category),
				Description: t.Description,
				Command:     cfg.Commands[t.Name],
				Status:      status,
				Duration:    fmtDuration(res.Duration),
				Stderr:      errMsg,
				Failed:      failed,
			})
			continue
		}

		errData, _ := os.ReadFile(filepath.Join(cfg.OutputDir, "errors", safeName+"_err.txt"))

		var output string
		var isFormatted bool

		switch t.OutputFormat {
		case "nmap_xml":
			formatted, err := report.FormatNmapXML(filepath.Join(cfg.OutputDir, "raw", "nmap.xml"))
			if err != nil {
				// Fallback: read raw stdout capture
				raw, _ := os.ReadFile(filepath.Join(cfg.OutputDir, "raw", safeName+".txt"))
				output = strings.TrimRight(string(raw), "\n")
			} else {
				output = strings.TrimRight(formatted, "\n")
				isFormatted = true
			}
		default:
			raw, _ := os.ReadFile(filepath.Join(cfg.OutputDir, "raw", safeName+".txt"))
			output = strings.TrimRight(string(raw), "\n")
		}

		toolResults = append(toolResults, report.ToolResult{
			Name:        t.Name,
			Category:    strings.ToUpper(t.Category),
			Description: t.Description,
			Command:     cfg.Commands[t.Name],
			Status:      status,
			Duration:    fmtDuration(res.Duration),
			Output:      output,
			Stderr:      strings.TrimRight(string(errData), "\n"),
			Failed:      failed,
			IsFormatted: isFormatted,
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

