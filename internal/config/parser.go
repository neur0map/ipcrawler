package config

import (
	"embed"
	"fmt"
	"io/fs"
	"path/filepath"
	"sort"

	"gopkg.in/yaml.v3"
)

// ParseTemplates walks the embedded templates directory tree, reading
// all .yaml files from category subdirectories (e.g. templates/dns/*.yaml).
func ParseTemplates(fsys embed.FS) ([]Template, error) {
	var templates []Template

	err := fs.WalkDir(fsys, "templates", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || filepath.Ext(d.Name()) != ".yaml" {
			return nil
		}

		data, err := fsys.ReadFile(path)
		if err != nil {
			return fmt.Errorf("reading %s: %w", path, err)
		}

		var t Template
		if err := yaml.Unmarshal(data, &t); err != nil {
			return fmt.Errorf("parsing %s: %w", path, err)
		}

		if err := validate(t, d.Name()); err != nil {
			return err
		}

		// Default priority to 50 if not specified
		if t.Priority == 0 {
			t.Priority = 50
		}

		templates = append(templates, t)
		return nil
	})
	if err != nil {
		return nil, err
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
