package wizard

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/help"
	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
	"github.com/neur0map/ipcrawler/internal/config"
	"golang.org/x/term"
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
	tDim    = lipgloss.Color("#707070") // Subdued but readable
	tRed    = lipgloss.Color("#FF4444")
	tGreen  = lipgloss.Color("#00FF00") // Success/selected checkmarks

	// High-contrast color pool for auto-assigning category colors.
	categoryColors = []lipgloss.Color{
		lipgloss.Color("#00FFFF"), // Cyan
		lipgloss.Color("#FFFF00"), // Yellow
		lipgloss.Color("#FF00FF"), // Magenta
		lipgloss.Color("#7FFFD4"), // Aquamarine
		lipgloss.Color("#FF69B4"), // Hot pink
		lipgloss.Color("#87CEEB"), // Sky blue
		lipgloss.Color("#FFD700"), // Gold
		lipgloss.Color("#DDA0DD"), // Plum
	}

	// Lazily populated map of category name → style.
	categoryStyleMap = make(map[string]lipgloss.Style)

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

// categoryColorFor returns a consistent color for any category.
// Colors are assigned on first encounter from the pool.
func categoryColorFor(cat string) lipgloss.Style {
	key := strings.ToLower(cat)
	if s, ok := categoryStyleMap[key]; ok {
		return s
	}
	color := categoryColors[len(categoryStyleMap)%len(categoryColors)]
	s := lipgloss.NewStyle().Foreground(color).Bold(true)
	categoryStyleMap[key] = s
	return s
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
	theme := tacticalTheme()

	var (
		target  string
		workers = 3
		verbose = false
	)

	for {
		// Step 1: Collect target + execution settings
		if err := collectSettings(theme, &target, &workers, &verbose); err != nil {
			return nil, err
		}

		// Step 2: Tool selection via custom picker
		targetType := detectTargetType(target)

		selected, err := runToolPicker(templates, target, targetType)
		if err != nil {
			return nil, err
		}
		if selected == nil {
			// User aborted the picker — restart from step 1
			continue
		}

		// Step 3: Wordlist selection (if fuzzing tools selected)
		var dirWordlist, vhostWordlist string
		if hasFeroxbuster(selected) {
			dirWordlist, err = collectWordlist(theme, "Feroxbuster", dirPresets)
			if err != nil {
				return nil, err
			}
		}
		if hasGobusterVHost(selected) {
			vhostWordlist, err = collectWordlist(theme, "Gobuster VHost", vhostPresets)
			if err != nil {
				return nil, err
			}
		}

		// Step 4: Nmap port override (if applicable)
		var nmapPorts string
		if hasNmap(selected) {
			nmapPorts, err = collectNmapPorts(theme)
			if err != nil {
				return nil, err
			}
		}

		// Build config
		cfg := buildConfig(target, templates, selected, workers, verbose)

		// Resolve {wordlist} placeholder per tool
		for name, cmd := range cfg.Commands {
			if !strings.Contains(cmd, "{wordlist}") {
				continue
			}
			lower := strings.ToLower(name)
			switch {
			case strings.Contains(lower, "feroxbuster"):
				cfg.Commands[name] = strings.ReplaceAll(cmd, "{wordlist}", dirWordlist)
			case strings.Contains(lower, "gobuster"):
				cfg.Commands[name] = strings.ReplaceAll(cmd, "{wordlist}", vhostWordlist)
			}
		}

		// Replace --top-ports 100 with custom -p spec if provided
		if nmapPorts = strings.TrimSpace(nmapPorts); nmapPorts != "" {
			for name, cmd := range cfg.Commands {
				if strings.Contains(strings.ToLower(name), "nmap") {
					cfg.Commands[name] = strings.Replace(cmd, "--top-ports 100", "-p "+nmapPorts, 1)
				}
			}
		}

		// Step 4: Summary + confirmation
		fmt.Println(renderSummary(cfg))

		var confirmed bool
		confirmForm := huh.NewForm(
			huh.NewGroup(
				huh.NewConfirm().
					Title("Execute?").
					Affirmative("Run!").
					Negative("Go back").
					Value(&confirmed),
			),
		).WithTheme(theme)

		if err := confirmForm.Run(); err != nil {
			return nil, err
		}

		if confirmed {
			// Pre-flight: check that selected tools are installed.
			if missing := checkTools(cfg.Tools, cfg.Commands); len(missing) > 0 {
				warn := lipgloss.NewStyle().Foreground(tRed).Bold(true)
				hint := lipgloss.NewStyle().Foreground(tDim)
				fmt.Println(warn.Render("\n  ✗ Missing tools:"))
				for _, bin := range missing {
					line := "    • " + bin
					if h, ok := installHints[bin]; ok {
						line += hint.Render("  (" + h + ")")
					}
					fmt.Println(line)
				}
				fmt.Println()

				var cont bool
				prompt := huh.NewForm(
					huh.NewGroup(
						huh.NewConfirm().
							Title("Continue without these tools?").
							Affirmative("Yes, skip them").
							Negative("No, go back").
							Value(&cont),
					),
				).WithTheme(theme)
				if err := prompt.Run(); err != nil {
					return nil, err
				}
				if !cont {
					continue
				}
				cfg.Tools, cfg.Commands = filterMissing(cfg.Tools, cfg.Commands, missing)
				if len(cfg.Tools) == 0 {
					fmt.Println(lipgloss.NewStyle().Foreground(tRed).Render(
						"\n  ✗ No tools remaining — returning to wizard\n"))
					continue
				}
			}

			if needsSudo(cfg.Tools, cfg.Commands) {
				if err := cacheSudoCredentials(); err != nil {
					fmt.Println(lipgloss.NewStyle().Foreground(tRed).Render(
						"\n  ✗ sudo authentication failed — returning to wizard\n"))
					continue
				}
			}
			return cfg, nil
		}
	}
}

// collectSettings runs the huh form for target + workers + display mode.
func collectSettings(theme *huh.Theme, target *string, workers *int, verbose *bool) error {
	form := huh.NewForm(
		huh.NewGroup(
			huh.NewInput().
				Title("Target").
				Description("IP address or domain").
				Placeholder("192.168.1.1 or example.com").
				Value(target).
				Validate(func(s string) error {
					if strings.TrimSpace(s) == "" {
						return fmt.Errorf("target cannot be empty")
					}
					return nil
				}),
		),
		huh.NewGroup(
			huh.NewSelect[int]().
				Title("Workers").
				Description("Parallel tool execution threads").
				Inline(true).
				Options(
					huh.NewOption("1 · Sequential", 1),
					huh.NewOption("3 · Default", 3),
					huh.NewOption("5 · Aggressive", 5),
					huh.NewOption("10 · Maximum", 10),
				).
				Value(workers),
			huh.NewSelect[bool]().
				Title("Display").
				Inline(true).
				Options(
					huh.NewOption("Minimal · Spinners", false),
					huh.NewOption("Verbose · Logs", true),
				).
				Value(verbose),
		),
	).WithLayout(huh.LayoutColumns(2)).WithTheme(theme)

	return form.Run()
}

// collectNmapPorts runs the port override form for nmap.
func collectNmapPorts(theme *huh.Theme) (string, error) {
	var nmapPorts string
	form := huh.NewForm(
		huh.NewGroup(
			huh.NewInput().
				Title("Nmap Ports").
				Description("Custom ports/range — leave empty for top 100").
				Placeholder("e.g. 80,443  or  1-1024  or  22,80,443-500").
				Value(&nmapPorts).
				Validate(func(s string) error {
					s = strings.TrimSpace(s)
					if s == "" {
						return nil
					}
					if !validPortSpec.MatchString(s) {
						return fmt.Errorf("invalid port spec (use digits, commas, dashes)")
					}
					return nil
				}),
		),
	).WithTheme(theme)

	if err := form.Run(); err != nil {
		return "", err
	}
	return strings.TrimSpace(nmapPorts), nil
}

// filterByTargetType returns templates compatible with the detected target type.
func filterByTargetType(templates []config.Template, targetType string) []config.Template {
	var out []config.Template
	for _, t := range templates {
		if isCompatible(t.TargetType, targetType) {
			out = append(out, t)
		}
	}
	return out
}

// termWidth returns the current terminal column count, falling back to 80.
func termWidth() int {
	w, _, err := term.GetSize(int(os.Stdout.Fd()))
	if err != nil || w <= 0 {
		return 80
	}
	return w
}

func buildConfig(target string, templates []config.Template, selected []string, workers int, verbose bool) *RunConfig {
	now := time.Now()
	timeStamp := now.Format("1504")
	dateStamp := now.Format("01-02")
	outputDir := filepath.Join("scans", fmt.Sprintf("%s_%s_%s", target, timeStamp, dateStamp))

	targetType := detectTargetType(target)
	tools := filterTemplates(templates, selected, targetType)

	rawDir := filepath.Join(outputDir, "raw")

	commands := make(map[string]string, len(tools))
	for _, t := range tools {
		cmd := t.ResolveCommand(target)
		cmd = strings.ReplaceAll(cmd, "{raw_dir}", rawDir)
		if t.Sudo {
			cmd = "sudo " + cmd
		}
		commands[t.Name] = cmd
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
	fmt.Fprintf(&sb, "%s  %s\n",
		metaKeyStyle.Render("Target:"),
		metaValStyle.Render(cfg.Target))
	fmt.Fprintf(&sb, "%s  %s\n",
		metaKeyStyle.Render("Workers:"),
		metaValStyle.Render(fmt.Sprintf("%d", cfg.Workers)))

	modeStr := "Minimal (Live tracking)"
	if cfg.Verbose {
		modeStr = "Verbose (Structured logs)"
	}
	fmt.Fprintf(&sb, "%s  %s\n",
		metaKeyStyle.Render("Mode:"),
		metaValStyle.Render(modeStr))
	fmt.Fprintf(&sb, "%s  %s\n",
		metaKeyStyle.Render("Output:"),
		metaValStyle.Render(cfg.OutputDir))
	sb.WriteString("\n")

	// Commands — grouped by category, yellow command text, truncated to fit
	w := termWidth()
	// box border(2) + padding(2) on each side = 8, plus "    $ " prefix = 6
	maxCmd := w - 8 - 6
	if maxCmd < 40 {
		maxCmd = 40
	}

	grouped := groupCommandsByCategory(cfg)
	for _, cat := range sortedCategories(grouped) {
		fmt.Fprintf(&sb, "  %s\n", summCatStyle.Render("── "+strings.ToUpper(cat)+" ──"))
		for _, entry := range grouped[cat] {
			display := entry
			if len(display) > maxCmd {
				display = display[:maxCmd-1] + "…"
			}
			fmt.Fprintf(&sb, "    %s\n", cmdStyle.Render("$ "+display))
		}
		sb.WriteString("\n")
	}

	return boxStyle.Width(w - 2).Render(sb.String())
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

func filterTemplates(templates []config.Template, selected []string, targetType string) []config.Template {
	set := make(map[string]bool, len(selected))
	for _, s := range selected {
		set[s] = true
	}
	var out []config.Template
	for _, t := range templates {
		if set[t.Name] && isCompatible(t.TargetType, targetType) {
			out = append(out, t)
		}
	}
	return out
}

// detectTargetType returns "ip", "domain", or "both" based on the input string.
func detectTargetType(target string) string {
	t := strings.TrimSpace(target)
	if t == "" {
		return "both"
	}
	if net.ParseIP(t) != nil {
		return "ip"
	}
	if _, _, err := net.ParseCIDR(t); err == nil {
		return "ip"
	}
	return "domain"
}

// hasNmap returns true if any selected tool name contains "nmap" (case-insensitive).
func hasNmap(selected []string) bool {
	for _, s := range selected {
		if strings.Contains(strings.ToLower(s), "nmap") {
			return true
		}
	}
	return false
}

// validPortSpec matches common nmap -p patterns: single ports, ranges, and
// comma-separated combos like "22,80,443-500".
var validPortSpec = regexp.MustCompile(`^[0-9]+([,-][0-9]+)*$`)

// needsSudo returns true if any selected tool requires elevated privileges,
// either via the Sudo field or inline "sudo " in the resolved command string.
func needsSudo(tools []config.Template, commands map[string]string) bool {
	for _, t := range tools {
		if t.Sudo {
			return true
		}
		if strings.Contains(commands[t.Name], "sudo ") {
			return true
		}
	}
	return false
}

// cacheSudoCredentials runs `sudo -v` to prompt for the user's password
// and cache credentials so subsequent sudo commands don't re-prompt.
func cacheSudoCredentials() error {
	cmd := exec.Command("sudo", "-v")
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// isCompatible returns true if a tool's target_type is compatible with the detected target.
func isCompatible(toolType, targetType string) bool {
	if toolType == "" || toolType == "both" || targetType == "both" {
		return true
	}
	return toolType == targetType
}
