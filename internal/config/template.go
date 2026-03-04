package config

import (
	"regexp"
	"strings"
	"time"
)

// Template defines a single tool's YAML schema.
// Each YAML file in templates/ maps directly to this struct.
type Template struct {
	Name        string   `yaml:"name"`
	Description string   `yaml:"description"`
	Command     string   `yaml:"command"`
	Category    string   `yaml:"category"`
	Timeout     string   `yaml:"timeout"`
	Tags        []string `yaml:"tags"`
}

// TimeoutDuration parses the timeout string into a time.Duration.
// Falls back to 5 minutes if the format is invalid.
func (t Template) TimeoutDuration() time.Duration {
	d, err := time.ParseDuration(t.Timeout)
	if err != nil {
		return 5 * time.Minute
	}
	return d
}

// ResolveCommand replaces the {target} placeholder with the actual target.
func (t Template) ResolveCommand(target string) string {
	return strings.ReplaceAll(t.Command, "{target}", target)
}

// SanitizeName converts a template name into a safe filename.
func SanitizeName(name string) string {
	re := regexp.MustCompile(`[^a-zA-Z0-9]+`)
	return strings.ToLower(strings.Trim(re.ReplaceAllString(name, "_"), "_"))
}
