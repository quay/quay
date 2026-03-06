package config

import (
	"fmt"
	"net"

	"github.com/distribution/distribution/v3/configuration"
)

// ToDistribution translates a Quay Config into a distribution Configuration.
// Only LocalStorage is currently supported.
func ToDistribution(cfg *Config) (*configuration.Configuration, error) {
	storagePath, err := ResolveStoragePath(cfg)
	if err != nil {
		return nil, err
	}

	distCfg := &configuration.Configuration{
		Storage: configuration.Storage{
			"filesystem": configuration.Parameters{
				"rootdirectory": storagePath,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
	}

	distCfg.HTTP.Addr = ResolveAddr(cfg.ServerHostname)

	return distCfg, nil
}

// ResolveStoragePath extracts the filesystem storage_path from the Quay config.
// It uses the first preference or the sole entry when only one is defined.
func ResolveStoragePath(cfg *Config) (string, error) {
	if len(cfg.DistributedStorageConfig) == 0 {
		return "", fmt.Errorf("no DISTRIBUTED_STORAGE_CONFIG defined")
	}

	var entry StorageEntry

	switch {
	case len(cfg.DistributedStoragePreference) > 0:
		id := cfg.DistributedStoragePreference[0]
		e, ok := cfg.DistributedStorageConfig[id]
		if !ok {
			return "", fmt.Errorf("preferred storage %q not found in DISTRIBUTED_STORAGE_CONFIG", id)
		}
		entry = e

	case len(cfg.DistributedStorageConfig) == 1:
		for _, e := range cfg.DistributedStorageConfig {
			entry = e
		}

	default:
		return "", fmt.Errorf("multiple storage entries defined but no DISTRIBUTED_STORAGE_PREFERENCE set")
	}

	if entry.Driver != "LocalStorage" {
		return "", fmt.Errorf("unsupported storage driver %q; only LocalStorage is currently supported", entry.Driver)
	}

	path, ok := entry.Params["storage_path"]
	if !ok {
		return "", fmt.Errorf("LocalStorage entry missing storage_path parameter")
	}

	pathStr, ok := path.(string)
	if !ok {
		return "", fmt.Errorf("storage_path must be a string, got %T", path)
	}

	return pathStr, nil
}

// ResolveAddr normalizes a SERVER_HOSTNAME value into a listen address.
// If the hostname includes a port it is used as-is; otherwise ":5000" is
// appended as a default.
func ResolveAddr(hostname string) string {
	if hostname == "" {
		return "127.0.0.1:5000"
	}
	_, _, err := net.SplitHostPort(hostname)
	if err != nil {
		return net.JoinHostPort(hostname, "5000")
	}
	return hostname
}
