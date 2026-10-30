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

func TestRunPurgeRejectsUnsafeDataDirFromQuadlet(t *testing.T) {
	for _, dataDir := range []string{"data", "/"} {
		t.Run(dataDir, func(t *testing.T) {
			env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
			qm := system.NewQuadletManager(system.OSFS{}, env)
			require.NoError(t, qm.Install("quay", &system.QuadletSpec{
				Image: "localhost/quay:test", DataDir: dataDir,
				Hostname: "localhost", Port: "8443",
			}))

			services := &recordingServiceManager{}
			fs := &noRemoveAllFS{}
			u := &Uninstaller{
				systemd: services,
				quadlet: qm,
				env:     env,
				fs:      fs,
			}

			err := u.Run(t.Context(), &Config{Purge: true})

			require.ErrorContains(t, err, "provide -data-dir explicitly")
			assert.Empty(t, services.calls, "must fail before touching the service")
			assert.True(t, qm.Exists("quay"))
			assert.Empty(t, fs.removed, "nothing may be removed")
		})
	}
}

func TestRunPurgeRejectsUnsafeExplicitDataDir(t *testing.T) {
	for _, dataDir := range []string{"/", "//", "data"} {
		t.Run(dataDir, func(t *testing.T) {
			env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
			services := &recordingServiceManager{}
			fs := &noRemoveAllFS{}
			u := &Uninstaller{
				systemd: services,
				quadlet: system.NewQuadletManager(system.OSFS{}, env),
				env:     env,
				fs:      fs,
			}

			err := u.Run(t.Context(), &Config{DataDir: dataDir, Purge: true})

			require.Error(t, err)
			assert.Empty(t, services.calls, "must fail before touching the service")
			assert.Empty(t, fs.removed, "nothing may be removed")
		})
	}
}

func TestRunWithoutPurgeAcceptsRelativeExplicitDataDir(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	fs := &noRemoveAllFS{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      fs,
	}

	err := u.Run(t.Context(), &Config{DataDir: "data"})

	require.NoError(t, err)
	assert.Contains(t, services.calls, "daemon-reload")
	assert.Empty(t, fs.removed)
}

func TestRunWithoutPurgeIgnoresRelativeDataDirFromQuadlet(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: "data",
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      system.OSFS{},
	}

	cfg := &Config{}
	err := u.Run(t.Context(), cfg)

	require.NoError(t, err)
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

func TestValidateDataDir(t *testing.T) {
	root, home := homeAliasLayout(t)
	require.NoError(t, os.Mkdir(filepath.Join(root, "opt"), 0o755))
	link := filepath.Join(root, "opt", "data-link")
	require.NoError(t, os.Symlink(filepath.Join(home, "data"), link))

	dangerous := []struct {
		path string
		desc string
	}{
		{"/", "root filesystem"},
		{".", "relative dot"},
		{home, "home directory"},
		{"///", "triple slash normalises to root"},
		{home + "/.", "home with trailing dot normalises to home"},
		{home + "/", "home with trailing slash"},
		{filepath.Join(root, "home", "u"), "home through a symlinked alias"},
		{filepath.Join(root, "var", "home"), "parent of home"},
		{home + "/..", "parent of home via dot-dot"},
		{link + "/..", "symlink into home then dot-dot"},
	}
	for _, tc := range dangerous {
		t.Run(tc.desc, func(t *testing.T) {
			assert.Error(t, validateDataDir(tc.path),
				"expected error for dangerous path %q", tc.path)
		})
	}

	safe := []struct {
		path string
		desc string
	}{
		{"/var/lib/quay", "standard quay data dir"},
		{"/opt/mirror-registry/data", "mirror-registry data dir"},
		{home + "/mirror-registry", "subdirectory of home"},
		{home + "/data", "existing subdirectory of home"},
		{filepath.Join(root, "srv", "quay"), "nonexistent directory"},
	}
	for _, tc := range safe {
		t.Run(tc.desc, func(t *testing.T) {
			assert.NoError(t, validateDataDir(tc.path),
				"unexpected error for safe path %q", tc.path)
		})
	}

	t.Run("HOME with trailing slash", func(t *testing.T) {
		t.Setenv("HOME", home+"/")
		assert.Error(t, validateDataDir(home))
	})

	t.Run("parent of home whose name starts with dot-dot", func(t *testing.T) {
		dir := t.TempDir()
		t.Setenv("HOME", filepath.Join(dir, "..u"))
		assert.Error(t, validateDataDir(dir))
	})
}

// homeAliasLayout mirrors Fedora atomic and RHEL image mode, where /home is a
// symlink to /var/home: HOME is <root>/var/home/u and <root>/home aliases
// <root>/var/home.
func homeAliasLayout(t *testing.T) (root, home string) {
	t.Helper()
	root = t.TempDir()
	home = filepath.Join(root, "var", "home", "u")
	require.NoError(t, os.MkdirAll(filepath.Join(home, "data"), 0o755))
	require.NoError(t, os.Symlink(filepath.Join(root, "var", "home"), filepath.Join(root, "home")))
	t.Setenv("HOME", home)
	return root, home
}

func TestRunRejectsUnsafeDataDirBeforePurge(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      &noRemoveAllFS{},
	}

	err := u.Run(t.Context(), &Config{DataDir: "/", Purge: true})

	require.ErrorContains(t, err, "refusing to remove root directory")
	// No service operations must have occurred before the guard fires.
	assert.Empty(t, services.calls)
}

func TestRunPurgeRejectsHomeAsExplicitDataDir(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	for _, dataDir := range []string{home, home + "/"} {
		t.Run(dataDir, func(t *testing.T) {
			env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
			qm := system.NewQuadletManager(system.OSFS{}, env)
			require.NoError(t, qm.Install("quay", &system.QuadletSpec{
				Image: "localhost/quay:test", DataDir: t.TempDir(),
				Hostname: "localhost", Port: "8443",
			}))

			services := &recordingServiceManager{}
			fs := &noRemoveAllFS{}
			u := &Uninstaller{
				systemd: services,
				quadlet: qm,
				env:     env,
				fs:      fs,
			}

			err := u.Run(t.Context(), &Config{DataDir: dataDir, Purge: true})

			require.ErrorContains(t, err, "refusing to remove home directory")
			assert.Empty(t, services.calls, "must fail before touching the service")
			assert.True(t, qm.Exists("quay"))
			assert.Empty(t, fs.removed, "nothing may be removed")
		})
	}
}

func TestRunPurgeRejectsHomeAliasAsExplicitDataDir(t *testing.T) {
	root, _ := homeAliasLayout(t)

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	fs := &noRemoveAllFS{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      fs,
	}

	err := u.Run(t.Context(), &Config{DataDir: filepath.Join(root, "home", "u"), Purge: true})

	require.ErrorContains(t, err, "refusing to remove home directory")
	assert.Empty(t, services.calls, "must fail before touching the service")
	assert.Empty(t, fs.removed, "nothing may be removed")
}

func TestRunPurgeRejectsHomeAsDataDirFromQuadlet(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	qm := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, qm.Install("quay", &system.QuadletSpec{
		Image: "localhost/quay:test", DataDir: home,
		Hostname: "localhost", Port: "8443",
	}))

	services := &recordingServiceManager{}
	fs := &noRemoveAllFS{}
	u := &Uninstaller{
		systemd: services,
		quadlet: qm,
		env:     env,
		fs:      fs,
	}

	err := u.Run(t.Context(), &Config{Purge: true})

	require.ErrorContains(t, err, "refusing to remove home directory")
	require.ErrorContains(t, err, "provide -data-dir explicitly")
	assert.Empty(t, services.calls, "must fail before touching the service")
	assert.True(t, qm.Exists("quay"))
	assert.Empty(t, fs.removed, "nothing may be removed")
}

func TestRunWithoutPurgeAcceptsHomeAsExplicitDataDir(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	services := &recordingServiceManager{}
	fs := &noRemoveAllFS{}
	u := &Uninstaller{
		systemd: services,
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		env:     env,
		fs:      fs,
	}

	err := u.Run(t.Context(), &Config{DataDir: home})

	require.NoError(t, err)
	assert.Contains(t, services.calls, "daemon-reload")
	assert.Empty(t, fs.removed)
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

// noRemoveAllFS records RemoveAll instead of deleting, so a regressed guard
// fails an assertion rather than removing "/" or the working directory.
type noRemoveAllFS struct {
	system.OSFS
	removed []string
}

func (f *noRemoveAllFS) RemoveAll(path string) error {
	f.removed = append(f.removed, path)
	return errors.New("RemoveAll disabled in test")
}
