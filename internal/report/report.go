package report

import (
	_ "embed"
	"fmt"
	"os"
	"path/filepath"
	"text/template"
)

//go:embed report.tmpl
var reportTmpl string

// ToolResult holds all metadata and output for a single tool execution.
type ToolResult struct {
	Name        string
	Category    string
	Description string
	Command     string // resolved command (no placeholders)
	Status      string // "Success" or "Failed"
	Duration    string // formatted duration
	Output      string // stdout content
	Stderr      string // stderr content
	Failed      bool
}

// ReportData is the top-level structure passed to the report template.
type ReportData struct {
	Target  string
	Date    string
	Results []ToolResult
}

// Compile executes the embedded report template against data and writes
// the result to {outputDir}/report.md.
func Compile(outputDir string, data ReportData) error {
	funcMap := template.FuncMap{
		"codeBlock": func(s string) string {
			return "```\n" + s + "\n```"
		},
	}

	tmpl, err := template.New("report").Funcs(funcMap).Parse(reportTmpl)
	if err != nil {
		return fmt.Errorf("parse template: %w", err)
	}

	reportPath := filepath.Join(outputDir, "report.md")
	f, err := os.Create(reportPath)
	if err != nil {
		return fmt.Errorf("create report: %w", err)
	}
	defer f.Close()

	if err := tmpl.Execute(f, data); err != nil {
		return fmt.Errorf("execute template: %w", err)
	}

	return nil
}
