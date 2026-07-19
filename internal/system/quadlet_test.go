package system

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestQuadletInstallUsesConfigPathWhenProvided(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)

	err := manager.Install("quay", &QuadletSpec{
		Image:      "localhost/quay:test",
		DataDir:    "/var/lib/quay",
		Hostname:   "localhost",
		Port:       "8443",
		ConfigPath: "/data/config.yaml",
	})
	if err != nil {
		t.Fatalf("Install: %v", err)
	}

	content := readQuadletTestFile(t, env.QuadletPath("quay"))
	if !strings.Contains(content, "Exec=serve --config /data/config.yaml --hostname localhost") {
		t.Fatalf("quadlet does not use config path:\n%s", content)
	}
	if strings.Contains(content, "--data-dir") {
		t.Fatalf("quadlet should not use default serve args when config path is set:\n%s", content)
	}
}

func TestQuadletInstallUsesDefaultServeArgsWithoutConfigPath(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)

	err := manager.Install("quay", &QuadletSpec{
		Image:    "localhost/quay:test",
		DataDir:  "/var/lib/quay",
		Hostname: "localhost",
		Port:     "8443",
	})
	if err != nil {
		t.Fatalf("Install: %v", err)
	}

	content := readQuadletTestFile(t, env.QuadletPath("quay"))
	if !strings.Contains(content, "Exec=serve --data-dir /data --hostname localhost:8443") {
		t.Fatalf("quadlet does not use default serve args:\n%s", content)
	}
}

func TestQuadletInstallMapsCustomHostPortToRegistryPort(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)

	err := manager.Install("quay", &QuadletSpec{
		Image:    "localhost/quay:test",
		DataDir:  "/var/lib/quay",
		Hostname: "localhost",
		Port:     "9443",
	})
	if err != nil {
		t.Fatalf("Install: %v", err)
	}

	content := readQuadletTestFile(t, env.QuadletPath("quay"))
	if !strings.Contains(content, "PublishPort=9443:8443") {
		t.Fatalf("quadlet does not map the custom host port to the registry port:\n%s", content)
	}
	if !strings.Contains(content, "--hostname localhost:9443") {
		t.Fatalf("quadlet does not advertise the custom host port:\n%s", content)
	}
}

func TestQuadletUpdateKeepsServerHostnameInSyncWithPublishedPort(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)

	err := manager.Install("quay", &QuadletSpec{
		Image:    "localhost/quay:old",
		DataDir:  "/var/lib/quay",
		Hostname: "registry.example.com",
		Port:     "8443",
	})
	if err != nil {
		t.Fatalf("Install: %v", err)
	}
	if err := manager.UpdateImageAndPort("quay", "localhost/quay:new", "9443"); err != nil {
		t.Fatalf("UpdateImageAndPort: %v", err)
	}

	content := readQuadletTestFile(t, env.QuadletPath("quay"))
	if !strings.Contains(content, "Image=localhost/quay:new") ||
		!strings.Contains(content, "PublishPort=9443:8443") ||
		!strings.Contains(content, "--hostname registry.example.com:9443") {
		t.Fatalf("quadlet update did not keep public endpoint in sync:\n%s", content)
	}
}

func TestQuadletUpdateAddsPublishedPortToLegacyDefaultCommand(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)
	path := env.QuadletPath("quay")
	if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
		t.Fatal(err)
	}
	legacy := "[Container]\nImage=localhost/quay:old\nPublishPort=8443:8443\nExec=serve --data-dir /data --hostname registry.example.com\n"
	if err := os.WriteFile(path, []byte(legacy), 0o600); err != nil {
		t.Fatal(err)
	}

	if err := manager.UpdateImageAndPort("quay", "localhost/quay:new", "9443"); err != nil {
		t.Fatalf("UpdateImageAndPort: %v", err)
	}
	content := readQuadletTestFile(t, path)
	if !strings.Contains(content, "--hostname registry.example.com:9443") {
		t.Fatalf("legacy command was not upgraded with public endpoint:\n%s", content)
	}
}

func TestQuadletInstallDoesNotPersistBootstrapCredentials(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)

	err := manager.Install("quay", &QuadletSpec{
		Image:    "localhost/quay:test",
		DataDir:  "/var/lib/quay",
		Hostname: "localhost",
		Port:     "8443",
	})
	if err != nil {
		t.Fatalf("Install: %v", err)
	}

	content := readQuadletTestFile(t, env.QuadletPath("quay"))
	if strings.Contains(content, "admin-username") || strings.Contains(content, "admin-password") {
		t.Fatalf("quadlet should not contain bootstrap credentials:\n%s", content)
	}
}

func TestQuadletHostname(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)
	require.NoError(t, manager.Install("quay", &QuadletSpec{
		Image:    "localhost/quay:test",
		DataDir:  "/var/lib/quay",
		Hostname: "registry.example.com",
		Port:     "8443",
	}))

	hostname, err := manager.Hostname("quay")

	require.NoError(t, err)
	assert.Equal(t, "registry.example.com", hostname)
}

func TestQuadletHostnameWithConfigPath(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)
	require.NoError(t, manager.Install("quay", &QuadletSpec{
		Image:      "localhost/quay:test",
		DataDir:    "/var/lib/quay",
		Hostname:   "registry.example.com",
		Port:       "8443",
		ConfigPath: "/data/config.yaml",
	}))

	hostname, err := manager.Hostname("quay")

	require.NoError(t, err)
	assert.Equal(t, "registry.example.com", hostname)
}

func readQuadletTestFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(filepath.Clean(path))
	if err != nil {
		t.Fatalf("read quadlet file: %v", err)
	}
	return string(data)
}
