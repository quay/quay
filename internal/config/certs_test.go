package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadCerts(t *testing.T) {
	dir := t.TempDir()

	// Create cert files that should be loaded.
	for _, name := range []string{"server.crt", "server.key", "ca.pem"} {
		require.NoError(t, os.WriteFile(filepath.Join(dir, name), []byte("FAKE "+name), 0o600))
	}

	// Create a non-cert file that should be ignored.
	require.NoError(t, os.WriteFile(filepath.Join(dir, "readme.txt"), []byte("ignored"), 0o600))

	certs, err := LoadCerts(dir)
	require.NoError(t, err)

	assert.Len(t, certs, 3)

	for _, name := range []string{"server.crt", "server.key", "ca.pem"} {
		assert.Contains(t, certs, name)
	}

	assert.NotContains(t, certs, "readme.txt")
}

func TestLoadCertsNonexistentDir(t *testing.T) {
	certs, err := LoadCerts("/nonexistent/path/that/does/not/exist")
	require.NoError(t, err)
	assert.Empty(t, certs)
}

func TestBuildTLSCertPoolExtraCACerts(t *testing.T) {
	dir := t.TempDir()
	extraDir := filepath.Join(dir, "extra_ca_certs")
	require.NoError(t, os.MkdirAll(extraDir, 0o755))

	// Write a non-extra cert that should not be added.
	require.NoError(t, os.WriteFile(filepath.Join(dir, "server.crt"), []byte("FAKE"), 0o600))

	certs, err := LoadCerts(dir)
	require.NoError(t, err)

	// With no extra_ca_certs PEM files, pool should still build fine.
	pool, err := BuildTLSCertPool(certs)
	require.NoError(t, err)
	require.NotNil(t, pool)
}
