package wizard

import (
	"fmt"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/help"
	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
	"github.com/neur0map/ipcrawler/internal/config"
)

// RunConfig holds the validated configuration produced by the wizard.
type RunConfig struct {
	Target    string
	Tools     []config.Template
	Workers   int
	Verbose   bool
	OutputDir string
	Commands  map[string]string // tool name → resolved command
}

// --- Home Depot Orange palette ---

var (
	tOrange = lipgloss.Color("#F96302") // Primary accent
	tCyan   = lipgloss.Color("#00FFFF") // Values in summary
	tYellow = lipgloss.Color("#FFD700") // Commands in summary
	tWhite  = lipgloss.Color("#FFFFFF")
	tGrayL  = lipgloss.Color("#B0B0B0") // Light gray for labels
	tGray   = lipgloss.Color("#6C6C6C") // Descriptions, inactive
	tDim    = lipgloss.Color("#3A3A3A") // Dark elements
	tRed    = lipgloss.Color("#FF4444")
	tGreen  = lipgloss.Color("#00FF00") // Success/selected checkmarks

	// Per-category colors for multi-select tags
	catDNS     = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FFFF")).Bold(true) // Cyan
	catNetwork = lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFF00")).Bold(true) // Yellow
	catWeb     = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF00FF")).Bold(true) // Magenta

	// Summary box styles
	headerStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(tOrange).
			Align(lipgloss.Center)

	metaKeyStyle = lipgloss.NewStyle().
			Foreground(tWhite).
			Bold(true).
			Width(14).
			Align(lipgloss.Right)

	metaValStyle = lipgloss.NewStyle().
			Foreground(tCyan)

	cmdStyle = lipgloss.NewStyle().
			Foreground(tYellow)

	summCatStyle = lipgloss.NewStyle().
			Foreground(tGrayL).
			Bold(true)

	boxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(tOrange).
			Padding(1, 2).
			MarginTop(1).
			MarginBottom(1)
)

// categoryColorFor returns the lipgloss style for a given category tag.
func categoryColorFor(cat string) lipgloss.Style {
	switch strings.ToLower(cat) {
	case "dns":
		return catDNS
	case "network":
		return catNetwork
	case "web":
		return catWeb
	default:
		return lipgloss.NewStyle().Foreground(tOrange).Bold(true)
	}
}

// tacticalTheme builds a custom huh theme with Home Depot Orange accents.
func tacticalTheme() *huh.Theme {
	t := huh.ThemeBase()

	// Focused field styles
	t.Focused.Base = t.Focused.Base.BorderForeground(tOrange)
	t.Focused.Card = t.Focused.Base
	t.Focused.Title = lipgloss.NewStyle().Foreground(tOrange).Bold(true)
	t.Focused.Description = lipgloss.NewStyle().Foreground(tGray)
	t.Focused.ErrorIndicator = lipgloss.NewStyle().Foreground(tRed).SetString(" *")
	t.Focused.ErrorMessage = lipgloss.NewStyle().Foreground(tRed)

	// Select cursor and navigation — orange
	t.Focused.SelectSelector = lipgloss.NewStyle().Foreground(tOrange).SetString("> ")
	t.Focused.NextIndicator = lipgloss.NewStyle().Foreground(tOrange).MarginLeft(1).SetString("→")
	t.Focused.PrevIndicator = lipgloss.NewStyle().Foreground(tOrange).MarginRight(1).SetString("←")
	t.Focused.Option = lipgloss.NewStyle().Foreground(tWhite)

	// Multi-select — orange cursor, green checkmarks
	t.Focused.MultiSelectSelector = lipgloss.NewStyle().Foreground(tOrange).SetString("> ")
	t.Focused.SelectedOption = lipgloss.NewStyle().Foreground(tGreen)
	t.Focused.SelectedPrefix = lipgloss.NewStyle().Foreground(tGreen).SetString("✓ ")
	t.Focused.UnselectedOption = lipgloss.NewStyle().Foreground(tGrayL)
	t.Focused.UnselectedPrefix = lipgloss.NewStyle().Foreground(tGray).SetString("· ")

	// Text input
	t.Focused.TextInput.Cursor = lipgloss.NewStyle().Foreground(tOrange)
	t.Focused.TextInput.Placeholder = lipgloss.NewStyle().Foreground(tGray)
	t.Focused.TextInput.Prompt = lipgloss.NewStyle().Foreground(tOrange)
	t.Focused.TextInput.Text = lipgloss.NewStyle().Foreground(tWhite)

	// Buttons — active: orange bg + black text, inactive: dark gray bg + white text
	t.Focused.FocusedButton = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#000000")).
		Background(tOrange).
		Bold(true).
		Padding(0, 2).
		MarginRight(1)
	t.Focused.BlurredButton = lipgloss.NewStyle().
		Foreground(tWhite).
		Background(lipgloss.Color("#2A2A2A")).
		Padding(0, 2).
		MarginRight(1)
	t.Focused.Next = t.Focused.FocusedButton

	// Blurred (inactive groups)
	t.Blurred = t.Focused
	t.Blurred.Base = t.Focused.Base.BorderStyle(lipgloss.HiddenBorder())
	t.Blurred.Card = t.Blurred.Base
	t.Blurred.NextIndicator = lipgloss.NewStyle()
	t.Blurred.PrevIndicator = lipgloss.NewStyle()

	// Group titles
	t.Group.Title = t.Focused.Title
	t.Group.Description = t.Focused.Description

	// Help text
	t.Help = help.New().Styles
	t.Help.ShortKey = lipgloss.NewStyle().Foreground(tGray)
	t.Help.ShortDesc = lipgloss.NewStyle().Foreground(tGray)
	t.Help.ShortSeparator = lipgloss.NewStyle().Foreground(tDim)

	return t
}

// Run launches the interactive wizard loop.
func Run(templates []config.Template) (*RunConfig, error) {
	var (
		target   string
		selected []string
		workers  int  = 3
		verbose  bool = false
	)

	theme := tacticalTheme()

	for {
		toolOptions := buildToolOptions(templates, selected)

		form := huh.NewForm(
			huh.NewGroup(
				huh.NewInput().
					Title("Target").
					Description("IP address or domain to scan").
					Placeholder("192.168.1.1").
					Value(&target).
					Validate(func(s string) error {
						if strings.TrimSpace(s) == "" {
							return fmt.Errorf("target cannot be empty")
						}
						return nil
					}),
			),

			huh.NewGroup(
				huh.NewMultiSelect[string]().
					Title("Tools").
					Description("Space to toggle · Enter to confirm · Shift+Tab to go back").
					Options(toolOptions...).
					Value(&selected).
					Filterable(true).
					Validate(func(s []string) error {
						if len(s) == 0 {
							return fmt.Errorf("select at least one tool")
						}
						return nil
					}),
			),

			huh.NewGroup(
				huh.NewSelect[int]().
					Title("Concurrency Limit").
					Description("Maximum tools running simultaneously").
					Options(
						huh.NewOption("1 — Sequential · Safest, avoids rate-limiting", 1),
						huh.NewOption("3 — Default · Balanced for general recon", 3),
						huh.NewOption("5 — Aggressive · May trigger WAFs or drop packets", 5),
						huh.NewOption("10 — Maximum · Likely to cause network instability", 10),
					).
					Value(&workers),
				huh.NewSelect[bool]().
					Title("Display Mode").
					Description("How tool output is displayed during execution").
					Options(
						huh.NewOption("Minimal · Live tracking with multi-spinner UI", false),
						huh.NewOption("Verbose · Structured logs streamed to terminal", true),
					).
					Value(&verbose),
			),
		).WithTheme(theme)

		if err := form.Run(); err != nil {
			return nil, err
		}

		cfg := buildConfig(target, templates, selected, workers, verbose)
		fmt.Println(renderSummary(cfg))

		var confirmed bool
		confirm := huh.NewForm(
			huh.NewGroup(
				huh.NewConfirm().
					Title("Execute?").
					Affirmative("Run!").
					Negative("Go back").
					Value(&confirmed),
			),
		).WithTheme(theme)

		if err := confirm.Run(); err != nil {
			return nil, err
		}

		if confirmed {
			return cfg, nil
		}
	}
}

// buildToolOptions creates multi-select options with color-coded category tags
// and column-aligned descriptions.
func buildToolOptions(templates []config.Template, selected []string) []huh.Option[string] {
	selectedSet := make(map[string]bool, len(selected))
	for _, s := range selected {
		selectedSet[s] = true
	}

	// Find the longest tool name for column alignment
	maxName := 0
	for _, t := range templates {
		if len(t.Name) > maxName {
			maxName = len(t.Name)
		}
	}

	var options []huh.Option[string]
	for _, t := range templates {
		// Pad the tag to a fixed visual width, then colorize it
		plainTag := fmt.Sprintf("%-10s", "["+strings.ToUpper(t.Category)+"]")
		coloredTag := categoryColorFor(t.Category).Render(plainTag)

		// Pad tool name so the colon separator aligns vertically
		paddedName := fmt.Sprintf("%-*s", maxName, t.Name)

		label := coloredTag + " " + paddedName + " : " + t.Description

		opt := huh.NewOption(label, t.Name)
		if selectedSet[t.Name] {
			opt = opt.Selected(true)
		}
		options = append(options, opt)
	}
	return options
}

func buildConfig(target string, templates []config.Template, selected []string, workers int, verbose bool) *RunConfig {
	now := time.Now()
	// Format: scans/{target}_HHmm_MM-DD
	timeStamp := now.Format("1504")
	dateStamp := now.Format("01-02")
	outputDir := filepath.Join("scans", fmt.Sprintf("%s_%s_%s", target, timeStamp, dateStamp))

	tools := filterTemplates(templates, selected)

	commands := make(map[string]string, len(tools))
	for _, t := range tools {
		commands[t.Name] = t.ResolveCommand(target)
	}

	return &RunConfig{
		Target:    target,
		Tools:     tools,
		Workers:   workers,
		Verbose:   verbose,
		OutputDir: outputDir,
		Commands:  commands,
	}
}

// renderSummary produces the redesigned confirmation box:
// orange border, white bold keys, cyan values, yellow commands.
func renderSummary(cfg *RunConfig) string {
	var sb strings.Builder

	sb.WriteString(headerStyle.Render("⚡ Run Configuration"))
	sb.WriteString("\n\n")

	// Metadata — white bold keys, cyan values
	sb.WriteString(fmt.Sprintf("%s  %s\n",
		metaKeyStyle.Render("Target:"),
		metaValStyle.Render(cfg.Target)))
	sb.WriteString(fmt.Sprintf("%s  %s\n",
		metaKeyStyle.Render("Workers:"),
		metaValStyle.Render(fmt.Sprintf("%d", cfg.Workers))))

	modeStr := "Minimal (Live tracking)"
	if cfg.Verbose {
		modeStr = "Verbose (Structured logs)"
	}
	sb.WriteString(fmt.Sprintf("%s  %s\n",
		metaKeyStyle.Render("Mode:"),
		metaValStyle.Render(modeStr)))
	sb.WriteString(fmt.Sprintf("%s  %s\n",
		metaKeyStyle.Render("Output:"),
		metaValStyle.Render(cfg.OutputDir)))
	sb.WriteString("\n")

	// Commands — grouped by category, yellow command text
	grouped := groupCommandsByCategory(cfg)
	for _, cat := range sortedCategories(grouped) {
		sb.WriteString(fmt.Sprintf("  %s\n", summCatStyle.Render("── "+strings.ToUpper(cat)+" ──")))
		for _, entry := range grouped[cat] {
			sb.WriteString(fmt.Sprintf("    %s\n", cmdStyle.Render("$ "+entry)))
		}
		sb.WriteString("\n")
	}

	return boxStyle.Render(sb.String())
}

func groupCommandsByCategory(cfg *RunConfig) map[string][]string {
	grouped := make(map[string][]string)
	for _, t := range cfg.Tools {
		grouped[t.Category] = append(grouped[t.Category], cfg.Commands[t.Name])
	}
	return grouped
}

func sortedCategories(grouped map[string][]string) []string {
	cats := make([]string, 0, len(grouped))
	for k := range grouped {
		cats = append(cats, k)
	}
	sort.Strings(cats)
	return cats
}

func filterTemplates(templates []config.Template, selected []string) []config.Template {
	set := make(map[string]bool, len(selected))
	for _, s := range selected {
		set[s] = true
	}
	var out []config.Template
	for _, t := range templates {
		if set[t.Name] {
			out = append(out, t)
		}
	}
	return out
}

func sanitizeTarget(target string) string {
	re := regexp.MustCompile(`[^a-zA-Z0-9]+`)
	s := re.ReplaceAllString(target, "_")
	return strings.Trim(s, "_")
}
