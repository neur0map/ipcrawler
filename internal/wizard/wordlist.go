package wizard

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
)

// wordlistPreset is a selectable wordlist option.
type wordlistPreset struct {
	Label    string // display name including line count
	RelPath  string // path relative to SecLists root
}

// Directory busting presets (feroxbuster)
var dirPresets = []wordlistPreset{
	{"raft-medium-directories.txt (~30k)", "Discovery/Web-Content/raft-medium-directories.txt"},
	{"directory-list-2.3-medium.txt (~220k)", "Discovery/Web-Content/directory-list-2.3-medium.txt"},
	{"common.txt (~4.7k)", "Discovery/Web-Content/common.txt"},
}

// VHost discovery presets (gobuster vhost)
var vhostPresets = []wordlistPreset{
	{"subdomains-top1million-5000.txt (~5k)", "Discovery/DNS/subdomains-top1million-5000.txt"},
	{"subdomains-top1million-20000.txt (~20k)", "Discovery/DNS/subdomains-top1million-20000.txt"},
	{"namelist.txt (~1.9k)", "Discovery/DNS/namelist.txt"},
}

// seclistsPaths are checked in order to find the SecLists installation.
var seclistsPaths = []string{
	"/usr/share/seclists",
	"/usr/share/SecLists",
	"/opt/homebrew/share/seclists",
}

// findSecLists returns the SecLists base directory, or empty string if not found.
func findSecLists() string {
	for _, p := range seclistsPaths {
		if info, err := os.Stat(p); err == nil && info.IsDir() {
			return p
		}
	}
	return ""
}

// hasFeroxbuster returns true if any selected tool name contains "feroxbuster".
func hasFeroxbuster(selected []string) bool {
	for _, s := range selected {
		if strings.Contains(strings.ToLower(s), "feroxbuster") {
			return true
		}
	}
	return false
}

// hasGobusterVHost returns true if any selected tool name contains "gobuster".
func hasGobusterVHost(selected []string) bool {
	for _, s := range selected {
		if strings.Contains(strings.ToLower(s), "gobuster") {
			return true
		}
	}
	return false
}

// collectWordlist shows a wordlist picker for a fuzzing tool.
// Returns the validated absolute path to the wordlist file.
func collectWordlist(theme *huh.Theme, toolLabel string, presets []wordlistPreset) (string, error) {
	secBase := findSecLists()

	// If SecLists not found, go straight to custom path input
	if secBase == "" {
		return collectCustomWordlist(theme, toolLabel,
			"SecLists not found — enter full wordlist path")
	}

	// Build select options from presets
	const customValue = "__custom__"
	options := make([]huh.Option[string], 0, len(presets)+1)
	for i, p := range presets {
		fullPath := filepath.Join(secBase, p.RelPath)
		label := p.Label
		if i == 0 {
			label += " (Recommended)"
		}
		options = append(options, huh.NewOption(label, fullPath))
	}
	options = append(options, huh.NewOption("Custom path", customValue))

	var selected string
	form := huh.NewForm(
		huh.NewGroup(
			huh.NewSelect[string]().
				Title(fmt.Sprintf("%s — Wordlist", toolLabel)).
				Options(options...).
				Value(&selected),
		),
	).WithTheme(theme)

	if err := form.Run(); err != nil {
		return "", err
	}

	if selected == customValue {
		return collectCustomWordlist(theme, toolLabel, "Enter wordlist path")
	}

	// Validate preset path exists
	if _, err := os.Stat(selected); err != nil {
		// Preset file missing — fall back to custom input with error
		return collectCustomWordlist(theme, toolLabel,
			fmt.Sprintf("File not found: %s — enter path", selected))
	}

	return selected, nil
}

// collectCustomWordlist prompts for a manual wordlist path with validation.
func collectCustomWordlist(theme *huh.Theme, toolLabel, prompt string) (string, error) {
	errStyle := lipgloss.NewStyle().Foreground(tRed)

	var wordlist string
	form := huh.NewForm(
		huh.NewGroup(
			huh.NewInput().
				Title(fmt.Sprintf("%s — Wordlist", toolLabel)).
				Description(prompt).
				Placeholder("/usr/share/seclists/Discovery/Web-Content/common.txt").
				Value(&wordlist).
				Validate(func(s string) error {
					s = strings.TrimSpace(s)
					if s == "" {
						return fmt.Errorf("wordlist path cannot be empty")
					}
					if _, err := os.Stat(s); err != nil {
						return fmt.Errorf("%s", errStyle.Render("file not found: "+s))
					}
					return nil
				}),
		),
	).WithTheme(theme)

	if err := form.Run(); err != nil {
		return "", err
	}
	return strings.TrimSpace(wordlist), nil
}
