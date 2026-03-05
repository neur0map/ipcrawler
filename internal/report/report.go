package report

import (
	"bytes"
	_ "embed"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"text/template"

	"github.com/vdjagilev/nmap-formatter/v3/formatter"
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
	IsFormatted bool // true = Output is already markdown, skip code block wrapping
}

// ReportData is the top-level structure passed to the report template.
type ReportData struct {
	Target  string
	Date    string
	Results []ToolResult
}

// Compile executes the embedded report template against data and writes
// the result to {outputDir}/report.md.
func Compile(outputDir string, data ReportData) (err error) {
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
	defer func() {
		if cerr := f.Close(); cerr != nil && err == nil {
			err = fmt.Errorf("close report: %w", cerr)
		}
	}()

	if err = tmpl.Execute(f, data); err != nil {
		return fmt.Errorf("execute template: %w", err)
	}

	return nil
}

// nopWriteCloser wraps an io.Writer into an io.WriteCloser with a no-op Close.
type nopWriteCloser struct{ io.Writer }

func (nopWriteCloser) Close() error { return nil }

// FormatNmapXML reads an nmap XML file and returns clean markdown via nmap-formatter.
func FormatNmapXML(xmlPath string) (string, error) {
	var buf bytes.Buffer

	cfg := &formatter.Config{
		Writer:       nopWriteCloser{&buf},
		OutputFormat: formatter.MarkdownOutput,
		InputFileConfig: formatter.InputFileConfig{
			Path: xmlPath,
		},
		OutputOptions: formatter.OutputOptions{
			MarkdownOptions: formatter.MarkdownOutputOptions{
				SkipHeader:     true,
				SkipTOC:        true,
				SkipMetrics:    true,
				SkipTraceroute: true,
				SkipPortScripts: true,
				SkipSummary:    true,
			},
		},
		SkipDownHosts: false,
	}

	wf := &formatter.MainWorkflow{}
	wf.SetConfig(cfg)
	wf.SetInputFile()
	if err := wf.Execute(); err != nil {
		return "", fmt.Errorf("nmap-formatter: %w", err)
	}

	return buf.String(), nil
}
