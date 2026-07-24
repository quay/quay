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
	if !strings.Contains(content, "Exec=serve --config /data/config.yaml --hostname localhost:8443\n") {
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
	if !strings.Contains(content, "Exec=serve --data-dir /data --hostname localhost:8443\n") {
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
	if !strings.Contains(content, "Exec=serve --data-dir /data --hostname localhost:9443\n") {
		t.Fatalf("quadlet does not pass the public host port to serve:\n%s", content)
	}
}

func TestQuadletServeCommandIncludesPublicPort(t *testing.T) {
	tests := []struct {
		name, hostname, port, want string
	}{
		{
			name: "dns", hostname: "registry.example.com", port: "9443",
			want: "serve --data-dir /data --hostname registry.example.com:9443",
		},
		{
			name: "ipv6", hostname: "2001:db8::1", port: "9443",
			want: "serve --data-dir /data --hostname [2001:db8::1]:9443",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, quadletServeCommand(&QuadletSpec{Hostname: tt.hostname, Port: tt.port}))
		})
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

func TestQuadletInstallVolumeHasUFlag(t *testing.T) {
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
	if !strings.Contains(content, "Volume=/var/lib/quay:/data:Z,U") {
		t.Fatalf("quadlet volume missing :U flag for UID remapping:\n%s", content)
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

func TestQuadletConfigPath(t *testing.T) {
	env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
	manager := NewQuadletManager(OSFS{}, env)
	require.NoError(t, manager.Install("quay", &QuadletSpec{
		Image: "localhost/quay:test", DataDir: "/var/lib/quay", Hostname: "registry.example.com",
		Port: "8443", ConfigPath: "/data/config.yaml",
	}))

	configPath, err := manager.ConfigPath("quay")

	require.NoError(t, err)
	assert.Equal(t, "/data/config.yaml", configPath)
}

func TestQuadletUpdateImageAndPortUpdatesAdvertisedHostname(t *testing.T) {
	tests := []struct {
		name, hostname, want string
	}{
		{name: "DNS", hostname: "registry.example.com", want: "registry.example.com:9443"},
		{name: "IPv6", hostname: "2001:db8::1", want: "[2001:db8::1]:9443"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			env := &Env{Mode: UserMode, HomeDir: t.TempDir()}
			manager := NewQuadletManager(OSFS{}, env)
			require.NoError(t, manager.Install("quay", &QuadletSpec{
				Image: "localhost/quay:old", DataDir: "/var/lib/quay", Hostname: tt.hostname, Port: "8443",
			}))

			require.NoError(t, manager.UpdateImageAndPort("quay", "localhost/quay:new", "9443"))

			content := readQuadletTestFile(t, env.QuadletPath("quay"))
			assert.Contains(t, content, "Image=localhost/quay:new")
			assert.Contains(t, content, "PublishPort=9443:8443")
			assert.Contains(t, content, "--hostname "+tt.want)
		})
	}
}

func TestUpdateServeHostnameRejectsMalformedHostname(t *testing.T) {
	_, _, err := updateServeHostname("serve --data-dir /data --hostname registry].example.com", "9443")

	assert.ErrorContains(t, err, "invalid hostname flag")
}

func readQuadletTestFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(filepath.Clean(path))
	if err != nil {
		t.Fatalf("read quadlet file: %v", err)
	}
	return string(data)
}
