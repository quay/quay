package uninstaller

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/system"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRunStopsServiceRemovesQuadletAndReloads(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir(), Username: "testuser"}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: "/var/lib/quay",
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: "/var/lib/quay"})

	require.NoError(t, err)
	assert.Equal(t, []string{"stop:quay", "daemon-reload", "disable-linger"}, services.calls)
	assert.False(t, qm.Exists("quay"))
}

func TestRunRemovesDataDirWhenPurge(t *testing.T) {
	dataDir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dataDir, "quay.db"), []byte("data"), 0o600))

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: dataDir,
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: dataDir, Purge: true})

	require.NoError(t, err)
	_, statErr := os.Stat(dataDir)
	assert.True(t, os.IsNotExist(statErr))
}

func TestRunPreservesDataDirWithoutPurge(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := filepath.Join(dataDir, "quay.db")
	require.NoError(t, os.WriteFile(dbPath, []byte("data"), 0o600))

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: dataDir,
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: dataDir})

	require.NoError(t, err)
	_, statErr := os.Stat(dbPath)
	assert.NoError(t, statErr)
}

func TestRunDisablesLingerForUserMode(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir(), Username: "testuser"}
	qm := system.NewQuadletManager(system.OSFS{}, env)

	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: "/var/lib/quay"})

	require.NoError(t, err)
	assert.Contains(t, services.calls, "disable-linger")
}

func TestRunSkipsLingerForRootMode(t *testing.T) {
	env := &system.Env{Mode: system.RootMode}
	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: "/var/lib/quay"})

	require.NoError(t, err)
	assert.NotContains(t, services.calls, "disable-linger")
}

func TestRunContinuesWhenServiceNotRunning(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{
		stopErr: fmt.Errorf("%w: quay", system.ErrUnitNotFound),
	}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: "/var/lib/quay"})

	require.NoError(t, err)
	assert.Contains(t, services.calls, "daemon-reload")
}

func TestRunFailsOnUnexpectedStopError(t *testing.T) {
	dataDir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dataDir, "quay.db"), []byte("data"), 0o600))

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: dataDir,
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{
		stopErr: errors.New("permission denied"),
	}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: dataDir, Purge: true})

	require.ErrorContains(t, err, "stop service")
	assert.NotContains(t, services.calls, "daemon-reload")
	_, statErr := os.Stat(filepath.Join(dataDir, "quay.db"))
	assert.NoError(t, statErr, "data should survive when stop fails even with purge")
}

func TestRunAutoDetectsDataDirFromQuadlet(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := filepath.Join(dataDir, "quay.db")
	require.NoError(t, os.WriteFile(dbPath, []byte("data"), 0o600))

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: dataDir,
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	cfg := &Config{Purge: true}
	err := u.Run(t.Context(), cfg)

	require.NoError(t, err)
	assert.Equal(t, dataDir, cfg.DataDir, "data dir should be resolved from quadlet")
	_, statErr := os.Stat(dataDir)
	assert.True(t, os.IsNotExist(statErr), "purge should delete the auto-detected data dir")
}

func TestRunPurgeFailsWhenNoDataDirAndNoQuadlet(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      system.OSFS{},
	}

	err := u.Run(t.Context(), &Config{Purge: true})

	require.ErrorContains(t, err, "resolve data directory")
	require.ErrorContains(t, err, "provide -data-dir explicitly")
	assert.Empty(t, services.calls, "must fail before touching the service")
}

func TestRunWithoutPurgeSucceedsWhenNoDataDirAndNoQuadlet(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      system.OSFS{},
	}

	cfg := &Config{}
	err := u.Run(t.Context(), cfg)

	require.NoError(t, err, "a non-purge uninstall has nothing to delete and must stay idempotent")
	assert.Empty(t, cfg.DataDir)
	assert.Contains(t, services.calls, "daemon-reload")
}

func TestRunIsIdempotent(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      system.OSFS{},
	}

	require.NoError(t, u.Run(t.Context(), &Config{DataDir: "/var/lib/quay"}))
	services.calls = nil
	require.NoError(t, u.Run(t.Context(), &Config{DataDir: "/var/lib/quay"}))
}

type recordingServiceManager struct {
	calls   []string
	stopErr error
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
	return r.stopErr
}

func (r *recordingServiceManager) EnableLinger(context.Context) error {
	r.calls = append(r.calls, "enable-linger")
	return nil
}

func (r *recordingServiceManager) DisableLinger(context.Context) error {
	r.calls = append(r.calls, "disable-linger")
	return nil
}

var _ system.ServiceManager = (*recordingServiceManager)(nil)
