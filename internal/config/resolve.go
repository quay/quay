package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Resolved holds a parsed Config together with the filesystem paths derived
// from it.
type Resolved struct {
	Config      *Config
	StoragePath string
	DBPath      string
}

// Resolve loads and resolves a complete configuration. If configPath is
// non-empty (or the QUAY_CONFIG env var is set), the config is loaded from
// that file and paths are resolved relative to its directory. Otherwise a
// default config is constructed using dataDir and hostname.
func Resolve(configPath, dataDir, hostname string) (*Resolved, error) {
	if configPath == "" {
		configPath = os.Getenv("QUAY_CONFIG")
	}
	if configPath != "" {
		return resolveFromFile(configPath)
	}
	return resolveFromDefaults(dataDir, hostname)
}

func resolveFromFile(configPath string) (*Resolved, error) {
	cfg, err := Load(configPath)
	if err != nil {
		return nil, err
	}
	configDir := filepath.Dir(configPath)
	storagePath, err := ResolveStoragePath(cfg, configDir)
	if err != nil {
		return nil, err
	}
	dbPath, err := ResolveDBPath(cfg, configDir)
	if err != nil {
		return nil, err
	}
	return &Resolved{Config: cfg, StoragePath: storagePath, DBPath: dbPath}, nil
}

func resolveFromDefaults(dataDir, hostname string) (*Resolved, error) {
	absDir, err := filepath.Abs(dataDir)
	if err != nil {
		return nil, fmt.Errorf("resolve data dir: %w", err)
	}
	storagePath := filepath.Join(absDir, "storage")

	for _, dir := range []string{absDir, storagePath} {
		if err := os.MkdirAll(dir, 0o750); err != nil {
			return nil, fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

	return &Resolved{
		Config:      NewDefault(hostname, storagePath),
		StoragePath: storagePath,
		DBPath:      filepath.Join(absDir, "quay.db"),
	}, nil
}

// ResolveDBPath extracts the SQLite database path from cfg.DBURI. If the path
// is relative, it is resolved against configDir (the directory containing the
// config file).
func ResolveDBPath(cfg *Config, configDir string) (string, error) {
	if cfg.DBURI == "" {
		return "", fmt.Errorf("DB_URI not set in config")
	}
	if !strings.HasPrefix(cfg.DBURI, "sqlite:///") {
		return "", fmt.Errorf("DB_URI must start with sqlite:/// for db commands (got %s)", cfg.DBURI)
	}
	dbPath := strings.TrimPrefix(cfg.DBURI, "sqlite:///")
	if !filepath.IsAbs(dbPath) {
		dbPath = filepath.Join(configDir, dbPath)
	}
	return dbPath, nil
}

// ResolveStoragePath extracts the storage_path from the single entry in
// cfg.DistributedStorageConfig. If the path is relative, it is resolved
// against configDir.
func ResolveStoragePath(cfg *Config, configDir string) (string, error) {
	if len(cfg.DistributedStorageConfig) == 0 {
		return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG is not set")
	}
	if len(cfg.DistributedStorageConfig) > 1 {
		return "", fmt.Errorf("multiple storage locations not supported; use a single entry in DISTRIBUTED_STORAGE_CONFIG")
	}

	for id, entry := range cfg.DistributedStorageConfig {
		path, ok := entry.Params["storage_path"].(string)
		if !ok || path == "" {
			return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG.%s: missing storage_path", id)
		}
		if !filepath.IsAbs(path) {
			path = filepath.Join(configDir, path)
		}
		return path, nil
	}

	return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG has no entries")
}

// NewDefault returns a Config suitable for standalone operation with the given
// hostname and local storage path.
func NewDefault(hostname, storagePath string) *Config {
	return &Config{
		Server: Server{
			ServerHostname:     hostname,
			PreferredURLScheme: "https",
		},
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"default": {
					Driver: "LocalStorage",
					Params: map[string]any{"storage_path": storagePath},
				},
			},
			DefaultTagExpiration: "2w",
		},
	}
}
