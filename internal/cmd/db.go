package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/quay/quay/internal/config"
)

// loadDBPath reads the config and extracts the SQLite file path from DB_URI.
// Relative paths are resolved against the config file's directory so the same
// config works inside the container (/data/config.yaml → /data/quay.db) and
// on the host (/var/lib/quay/config.yaml → /var/lib/quay/quay.db).
func loadDBPath(configPath string) (string, error) {
	cfg, err := config.Load(configPath)
	if err != nil {
		return "", fmt.Errorf("load config: %w", err)
	}

	if cfg.DBURI == "" {
		return "", fmt.Errorf("DB_URI not set in config")
	}

	if !strings.HasPrefix(cfg.DBURI, "sqlite:///") {
		return "", fmt.Errorf("DB_URI must start with sqlite:/// for db commands (got %s)", cfg.DBURI)
	}

	dbPath := strings.TrimPrefix(cfg.DBURI, "sqlite:///")

	if !filepath.IsAbs(dbPath) {
		dbPath = filepath.Join(filepath.Dir(configPath), dbPath)
	}

	return dbPath, nil
}

// resolveConfigPath returns the config path from the flag, QUAY_CONFIG env, or default.
func resolveConfigPath(flagValue string) string {
	if flagValue != "" {
		return flagValue
	}
	if env := os.Getenv("QUAY_CONFIG"); env != "" {
		return env
	}
	return "config.yaml"
}

