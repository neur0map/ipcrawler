package wizard

import (
	"os/exec"
	"regexp"
	"strings"

	"github.com/neur0map/ipcrawler/internal/config"
)

// installHints maps binary names to install commands (macOS-oriented).
var installHints = map[string]string{
	"nmap":      "brew install nmap",
	"dig":       "brew install bind",
	"whois":     "brew install whois",
	"curl":      "brew install curl",
	"subfinder": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
	"dnsx":      "go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
	"hakrevdns":  "go install -v github.com/hakluke/hakrevdns@latest",
	"amass":      "go install -v github.com/owasp-amass/amass/v4/...@master",
	"dnsrecon":   "pip install dnsrecon",
	"feroxbuster": "brew install feroxbuster",
	"gobuster":   "go install -v github.com/OJ/gobuster/v3@latest",
}

// skipBinaries are shell builtins and coreutils that are always present.
var skipBinaries = map[string]bool{
	"sudo": true, "sh": true, "bash": true,
	"[": true, "test": true, "echo": true,
	"cat": true, "tee": true, "awk": true,
	"sed": true, "grep": true, "sort": true,
	"head": true, "tail": true, "cut": true,
	"tr": true, "wc": true, "uniq": true,
	"true": true, "false": true, "printf": true,
}

// splitPipe splits a shell command on |, &&, and || into segments.
var splitPipe = regexp.MustCompile(`\|{1,2}|&&`)

// validBinary matches tokens that look like an executable name:
// letters, digits, hyphens, underscores — no dots, slashes, or special chars.
var validBinary = regexp.MustCompile(`^[a-zA-Z][a-zA-Z0-9_-]*$`)

// stripQuoted removes single-quoted and double-quoted strings so the
// splitter doesn't cut through shell arguments like awk patterns.
var stripQuoted = regexp.MustCompile(`'[^']*'|"[^"]*"`)

// extractBinaries parses a shell command string and returns the external
// binary names it invokes. Skips builtins, coreutils, and sudo prefixes.
func extractBinaries(command string) []string {
	seen := map[string]bool{}
	var bins []string

	// Remove quoted strings before splitting so pipes inside awk/sed
	// patterns don't create bogus segments.
	cleaned := stripQuoted.ReplaceAllString(command, "")

	for _, seg := range splitPipe.Split(cleaned, -1) {
		fields := strings.Fields(strings.TrimSpace(seg))
		if len(fields) == 0 {
			continue
		}

		// The first token is the command. Walk past "sudo" prefixes only
		// (sudo is a prefix, not a command in this context). Then check
		// if the resulting command is a known builtin — if so, skip the
		// entire segment (remaining tokens are arguments, not binaries).
		for len(fields) > 0 && fields[0] == "sudo" {
			fields = fields[1:]
		}
		if len(fields) == 0 {
			continue
		}

		bin := fields[0]
		// If the command is a known builtin/coreutil, skip the whole
		// segment — everything after it is arguments, not commands.
		if skipBinaries[bin] {
			continue
		}
		// Only accept tokens that look like a binary name: alphanumeric
		// with optional hyphens/underscores (e.g. "nmap", "hakrevdns",
		// "dnsx"). Skip everything else — flags, paths, IPs, awk args.
		if !validBinary.MatchString(bin) {
			continue
		}
		if !seen[bin] {
			seen[bin] = true
			bins = append(bins, bin)
		}
	}
	return bins
}

// checkTools returns binary names that are referenced by selected tools
// but not found on PATH.
func checkTools(tools []config.Template, commands map[string]string) []string {
	seen := map[string]bool{}
	var missing []string

	for _, t := range tools {
		for _, bin := range extractBinaries(commands[t.Name]) {
			if seen[bin] {
				continue
			}
			seen[bin] = true
			if _, err := exec.LookPath(bin); err != nil {
				missing = append(missing, bin)
			}
		}
	}
	return missing
}

// filterMissing removes templates that depend on a missing binary, plus
// any templates whose depends_on references a removed template.
func filterMissing(tools []config.Template, commands map[string]string, missing []string) ([]config.Template, map[string]string) {
	missingSet := map[string]bool{}
	for _, b := range missing {
		missingSet[b] = true
	}

	// First pass: find templates that directly use a missing binary.
	removed := map[string]bool{}
	for _, t := range tools {
		for _, bin := range extractBinaries(commands[t.Name]) {
			if missingSet[bin] {
				removed[t.Name] = true
				break
			}
		}
	}

	// Second pass: also remove templates that depend on a removed template.
	changed := true
	for changed {
		changed = false
		for _, t := range tools {
			if removed[t.Name] {
				continue
			}
			for _, dep := range t.DependsOn {
				if removed[dep] {
					removed[t.Name] = true
					changed = true
					break
				}
			}
		}
	}

	// Build filtered slices.
	var kept []config.Template
	keptCmds := make(map[string]string)
	for _, t := range tools {
		if !removed[t.Name] {
			kept = append(kept, t)
			keptCmds[t.Name] = commands[t.Name]
		}
	}
	return kept, keptCmds
}
