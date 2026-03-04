package config

import (
	"embed"
	"fmt"
	"path/filepath"
	"sort"

	"gopkg.in/yaml.v3"
)

// ParseTemplates reads all .yaml files from the embedded filesystem,
// validates them, and returns them sorted by category then name.
func ParseTemplates(fs embed.FS) ([]Template, error) {
	entries, err := fs.ReadDir("templates")
	if err != nil {
		return nil, fmt.Errorf("reading templates directory: %w", err)
	}

	var templates []Template
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".yaml" {
			continue
		}

		data, err := fs.ReadFile(filepath.Join("templates", entry.Name()))
		if err != nil {
			return nil, fmt.Errorf("reading %s: %w", entry.Name(), err)
		}

		var t Template
		if err := yaml.Unmarshal(data, &t); err != nil {
			return nil, fmt.Errorf("parsing %s: %w", entry.Name(), err)
		}

		if err := validate(t, entry.Name()); err != nil {
			return nil, err
		}

		templates = append(templates, t)
	}

	sort.Slice(templates, func(i, j int) bool {
		if templates[i].Category == templates[j].Category {
			return templates[i].Name < templates[j].Name
		}
		return templates[i].Category < templates[j].Category
	})

	return templates, nil
}

// validate checks that required fields are present.
func validate(t Template, filename string) error {
	if t.Name == "" {
		return fmt.Errorf("%s: missing required field 'name'", filename)
	}
	if t.Command == "" {
		return fmt.Errorf("%s: missing required field 'command'", filename)
	}
	if t.Category == "" {
		return fmt.Errorf("%s: missing required field 'category'", filename)
	}
	return nil
}
