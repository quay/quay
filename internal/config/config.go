// Package config provides Quay configuration parsing, defaults, and validation.
//
// The Config struct uses embedded types for logical grouping (Server, Database,
// Storage, etc.) while remaining a single struct for yaml.Unmarshal. A two-pass
// parse detects unknown YAML keys; the typed embedded structs use yaml:",inline"
// for flattening while the raw map pass catches anything not in the struct.
package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Config is the top-level Quay configuration.
type Config struct {
	Server   `yaml:",inline"`
	Database `yaml:",inline"`
	Storage  `yaml:",inline"`
	Redis    `yaml:",inline"`
	Auth     `yaml:",inline"`
	Features `yaml:",inline"`
	Security `yaml:",inline"`
	Keys     `yaml:",inline"`

	// Extra holds YAML keys not mapped to struct fields.
	// The Python config has 200+ keys; the Go struct covers a subset.
	// Unknown keys are tracked here to warn about possible typos, preserve
	// forward compatibility with new keys, and provide visibility into
	// configuration that is not yet validated by the Go parser.
	// Populated by the two-pass parse; never written to the YAML output.
	Extra map[string]any `yaml:"-"`
}

// Load reads a config file from disk and parses it. path may be a file or a
// directory containing config.yaml.
func Load(path string) (*Config, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, fmt.Errorf("config: stat %s: %w", path, err)
	}
	if info.IsDir() {
		path = filepath.Join(path, "config.yaml")
	}

	data, err := os.ReadFile(path) //nolint:gosec // path is a user-provided config file
	if err != nil {
		return nil, fmt.Errorf("config: read %s: %w", path, err)
	}

	return Parse(data)
}

// Parse unmarshals YAML data into a Config, detects unknown keys, and applies
// defaults. This is the two-pass parse described in the design:
//
//  1. Start from a default-populated Config (newDefaultConfig).
//  2. Unmarshal into the typed Config struct (overwriting only present keys).
//  3. Unmarshal into a raw map.
//  4. Diff raw map keys against known yaml tags → populate Extra.
func Parse(data []byte) (*Config, error) {
	cfg := newDefaultConfig()

	// Pass 1: typed struct. Defaults are pre-populated; YAML overwrites
	// only keys present in the input.
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("config: parse: %w", err)
	}

	// Pass 2: raw map for unknown-key detection.
	var raw map[string]any
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("config: parse raw: %w", err)
	}

	known := knownYAMLTags(cfg)
	cfg.Extra = make(map[string]any)
	for k, v := range raw {
		if !known[k] {
			cfg.Extra[k] = v
		}
	}

	return &cfg, nil
}
