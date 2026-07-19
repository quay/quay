package installer

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/system"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUpgradeUsesEffectivePort(t *testing.T) {
	tests := []struct {
		name          string
		requestedPort string
		wantPort      string
	}{
		{
			name:          "explicit port replaces existing port",
			requestedPort: "10443",
			wantPort:      "10443",
		},
		{
			name:     "omitted port preserves existing port",
			wantPort: "9443",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
			quadlet := system.NewQuadletManager(system.OSFS{}, env)
			require.NoError(t, quadlet.Install(quadletServiceName, &system.QuadletSpec{
				Image:    "localhost/quay:old",
				DataDir:  "/var/lib/quay",
				Hostname: "registry.example.com",
				Port:     "9443",
			}))

			services := &recordingServiceManager{}
			inst := &Installer{
				systemd: services,
				quadlet: quadlet,
				env:     env,
			}

			port, err := inst.resolvePort(tt.requestedPort, true)
			require.NoError(t, err)
			require.Equal(t, tt.wantPort, port)
			require.NoError(t, inst.upgrade(t.Context(), "localhost/quay:new", port))

			content, err := os.ReadFile(env.QuadletPath(quadletServiceName))
			require.NoError(t, err)
			assert.Contains(t, string(content), "Image=localhost/quay:new")
			assert.Contains(t, string(content), "PublishPort="+tt.wantPort+":8443")
			assert.Equal(t, []string{"stop:quay", "daemon-reload", "start:quay"}, services.calls)
		})
	}
}

func TestResolvePortDefaultsFreshInstall(t *testing.T) {
	inst := &Installer{}

	port, err := inst.resolvePort("", false)

	require.NoError(t, err)
	assert.Equal(t, "8443", port)
}

func TestRunReportsQuadletPortResolutionErrors(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	quadlet := system.NewQuadletManager(system.OSFS{}, env)
	quadletPath := env.QuadletPath(quadletServiceName)
	require.NoError(t, os.MkdirAll(filepath.Dir(quadletPath), 0o755))
	require.NoError(t, os.WriteFile(quadletPath, []byte("[Container]\nImage=localhost/quay:test\n"), 0o600))

	inst := &Installer{quadlet: quadlet}
	err := inst.Run(t.Context(), &Config{})

	require.ErrorContains(t, err, "resolve port: determine existing port")
	assert.NotContains(t, err.Error(), "invalid port")
}

type recordingServiceManager struct {
	calls []string
}

func (r *recordingServiceManager) DaemonReload(context.Context) error {
	r.calls = append(r.calls, "daemon-reload")
	return nil
}

func (r *recordingServiceManager) Start(_ context.Context, service string) error {
	r.calls = append(r.calls, "start:"+service)
	return nil
}

func (r *recordingServiceManager) Stop(_ context.Context, service string) error {
	r.calls = append(r.calls, "stop:"+service)
	return nil
}

func (r *recordingServiceManager) EnableLinger(context.Context) error {
	return nil
}

var _ system.ServiceManager = (*recordingServiceManager)(nil)
