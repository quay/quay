package config

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestToDistribution_LocalStorage(t *testing.T) {
	cfg := &Config{
		Server: Server{ServerHostname: "localhost:9090"},
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"default": {Driver: "LocalStorage", Params: map[string]any{"storage_path": "/data/registry"}},
			},
			DistributedStoragePreference: []string{"default"},
		},
	}

	distCfg, err := ToDistribution(cfg)
	require.NoError(t, err)

	assert.Equal(t, "localhost:9090", distCfg.HTTP.Addr)
	assert.Equal(t, "/data/registry", distCfg.Storage["filesystem"]["rootdirectory"])
	assert.Equal(t, true, distCfg.Storage["delete"]["enabled"])
}

func TestToDistribution_UnsupportedDriver(t *testing.T) {
	cfg := &Config{
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"s3": {Driver: "S3Storage", Params: map[string]any{"s3_bucket": "mybucket"}},
			},
			DistributedStoragePreference: []string{"s3"},
		},
	}

	_, err := ToDistribution(cfg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "unsupported storage driver")
}

func TestToDistribution_NoStorageConfig(t *testing.T) {
	cfg := &Config{}

	_, err := ToDistribution(cfg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "no DISTRIBUTED_STORAGE_CONFIG")
}

func TestToDistribution_MissingStoragePath(t *testing.T) {
	cfg := &Config{
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"default": {Driver: "LocalStorage", Params: map[string]any{}},
			},
			DistributedStoragePreference: []string{"default"},
		},
	}

	_, err := ToDistribution(cfg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "missing storage_path")
}

func TestResolveAddr(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"localhost:8080", "localhost:8080"},
		{"quay.example.com", "quay.example.com:5000"},
		{"", "127.0.0.1:5000"},
		{"0.0.0.0:5000", "0.0.0.0:5000"},
		{"::1", "[::1]:5000"},
		{"[::1]:8080", "[::1]:8080"},
	}
	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			assert.Equal(t, tt.want, ResolveAddr(tt.input))
		})
	}
}

func TestResolveStoragePath_PreferenceOverride(t *testing.T) {
	cfg := &Config{
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"primary":   {Driver: "LocalStorage", Params: map[string]any{"storage_path": "/primary"}},
				"secondary": {Driver: "LocalStorage", Params: map[string]any{"storage_path": "/secondary"}},
			},
			DistributedStoragePreference: []string{"secondary"},
		},
	}

	path, err := ResolveStoragePath(cfg)
	require.NoError(t, err)
	assert.Equal(t, "/secondary", path)
}

func TestResolveStoragePath_SingleEntryNoPreference(t *testing.T) {
	cfg := &Config{
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"only": {Driver: "LocalStorage", Params: map[string]any{"storage_path": "/only"}},
			},
		},
	}

	path, err := ResolveStoragePath(cfg)
	require.NoError(t, err)
	assert.Equal(t, "/only", path)
}

func TestResolveStoragePath_MultipleNoPreference(t *testing.T) {
	cfg := &Config{
		Storage: Storage{
			DistributedStorageConfig: StorageEntries{
				"a": {Driver: "LocalStorage", Params: map[string]any{"storage_path": "/a"}},
				"b": {Driver: "LocalStorage", Params: map[string]any{"storage_path": "/b"}},
			},
		},
	}

	_, err := ResolveStoragePath(cfg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "no DISTRIBUTED_STORAGE_PREFERENCE")
}
