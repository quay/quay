package migrate

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"

	"github.com/quay/quay/internal/dal/dbcore"
)

func TestPostgresLoopbackURI(t *testing.T) {
	const raw = "postgresql://user:p%40ss@quay-postgres:5432/quay"
	got, err := postgresLoopbackURI(raw)
	if err != nil {
		t.Fatalf("postgresLoopbackURI: %v", err)
	}
	u, err := url.Parse(got)
	if err != nil {
		t.Fatal(err)
	}
	if u.Hostname() != "127.0.0.1" || u.Port() != "5432" || u.Path != "/quay" {
		t.Fatalf("rewritten URI changed more than the host: %s", u.Redacted())
	}
	password, _ := u.User.Password()
	if u.User.Username() != "user" || password != "p@ss" {
		t.Fatal("rewritten URI changed credentials")
	}
}

func TestPostgresLoopbackURIRejectsUnsupportedEndpointWithoutLeakingPassword(t *testing.T) {
	const secret = "do-not-print-this"
	_, err := postgresLoopbackURI("postgresql://user:" + secret + "@other-postgres/quay")
	if err == nil {
		t.Fatal("unsupported PostgreSQL endpoint was accepted")
	}
	if strings.Contains(err.Error(), secret) {
		t.Fatalf("error leaked password: %v", err)
	}
}

func TestPostgresLoopbackURIRejectsQueryOverrides(t *testing.T) {
	_, err := postgresLoopbackURI("postgresql://user:password@quay-postgres/quay?host=other-postgres")
	if err == nil {
		t.Fatal("DB_URI query override was accepted")
	}
}

func TestPostgresConnectionErrorPreservesRedactedCause(t *testing.T) {
	listener, err := (&net.ListenConfig{}).Listen(t.Context(), "tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	accepted := make(chan struct{})
	go func() {
		defer close(accepted)
		conn, err := listener.Accept()
		if err == nil {
			_ = conn.Close()
		}
	}()
	t.Cleanup(func() { _ = listener.Close() })

	const secret = "sentinel-password-must-not-appear"
	ctx, cancel := context.WithTimeout(t.Context(), 3*time.Second)
	defer cancel()
	conn, err := pgx.Connect(ctx, fmt.Sprintf("postgresql://quay:%s@%s/quay?sslmode=disable", secret, listener.Addr()))
	if conn != nil {
		_ = conn.Close(context.Background())
	}
	if err == nil {
		t.Fatal("pgx.Connect unexpectedly succeeded")
	}
	got := postgresConnectionError(err)
	if strings.Contains(got.Error(), secret) {
		t.Fatalf("connection error leaked password: %v", got)
	}
	if got.Error() == "connect to source PostgreSQL: connection failed" {
		t.Fatalf("connection error discarded safe cause: %v", got)
	}
	select {
	case <-accepted:
	case <-time.After(3 * time.Second):
		t.Fatal("test PostgreSQL listener did not accept a connection")
	}

	got = postgresConnectionError(errors.New("untrusted error containing " + secret))
	if strings.Contains(got.Error(), secret) {
		t.Fatalf("unclassified connection error leaked password: %v", got)
	}
}

func TestCreateIntermediateDatabaseFileUsesPrivatePermissions(t *testing.T) {
	path := filepath.Join(t.TempDir(), partialDatabaseName)
	if err := createIntermediateDatabaseFile(path); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if got := info.Mode().Perm(); got != 0o600 {
		t.Fatalf("intermediate database permissions = %04o, want 0600", got)
	}
	if err := createIntermediateDatabaseFile(path); err == nil {
		t.Fatal("createIntermediateDatabaseFile unexpectedly overwrote an existing file")
	}
}

func TestInPostgresNetworkNamespace(t *testing.T) {
	m := &Migrator{Source: OMRSource{PodSandboxKey: "/proc/self/ns/net"}}
	inside, err := m.inPostgresNetworkNamespace()
	if err != nil || !inside {
		t.Fatalf("inPostgresNetworkNamespace = %t, %v", inside, err)
	}
}

func TestRunPostgresCopyInNamespaceBuildsRootlessAndRootfulCommands(t *testing.T) {
	for _, tc := range []struct {
		name  string
		scope string
		want  string
	}{
		{name: "rootless", scope: scopeUser, want: "podman unshare nsenter --net=/run/netns/quay"},
		{name: "rootful", scope: scopeSystem, want: "nsenter --net=/run/netns/quay"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			runner := &recordingRunner{}
			m := &Migrator{
				DataDir: "/target",
				Runner:  runner,
				Source: OMRSource{
					ConfigDir:     "/source/config",
					SystemdScope:  tc.scope,
					PodSandboxKey: "/run/netns/quay",
				},
			}
			if err := m.runPostgresCopyInNamespace(t.Context()); err != nil {
				t.Fatal(err)
			}
			if len(runner.runCalls) != 1 || !strings.HasPrefix(runner.runCalls[0], tc.want) {
				t.Fatalf("namespace command = %v, want prefix %q", runner.runCalls, tc.want)
			}
			if !strings.Contains(runner.runCalls[0], "migrate -data-dir=/target -source-certs=/source/config") {
				t.Fatalf("namespace argv did not preserve migrate paths: %s", runner.runCalls[0])
			}
			if strings.Contains(runner.runCalls[0], "postgresql://") {
				t.Fatalf("namespace argv contains database URI: %s", runner.runCalls[0])
			}
		})
	}
}

func TestRunPostgresMigrationStopsOnlyAppBeforeConversionAndRollsBack(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	m := validInstallMigrator(t)
	m.Source.DatabaseKind = databasePostgres
	m.Source.SystemdScope = scopeUser
	m.Source.PodSandboxKey = "/run/netns/quay"
	runner := &sequenceRunner{
		namespaceErr: errors.New("conversion failed"),
		namespaceHook: func() {
			partialPath := m.postgresPartialDBPath()
			for _, path := range []string{partialPath, partialPath + "-wal", partialPath + "-shm", filepath.Join(m.DataDir, "quay.db")} {
				if err := os.WriteFile(path, []byte("failed migration artifact"), 0o600); err != nil {
					t.Fatal(err)
				}
			}
		},
	}
	m.Runner = runner

	err := m.runPostgresMigration(t.Context())
	if err == nil || !strings.Contains(err.Error(), "conversion failed") {
		t.Fatalf("runPostgresMigration error = %v", err)
	}
	want := []string{
		"systemctl --user stop quay-app.service",
		"podman unshare nsenter --net=/run/netns/quay",
		"systemctl --user start quay-pod.service",
		"systemctl --user start quay-postgres.service",
		"systemctl --user start quay-redis.service",
		"systemctl --user start quay-app.service",
	}
	if len(runner.calls) != len(want) {
		t.Fatalf("calls = %v, want %v", runner.calls, want)
	}
	for i := range want {
		if !strings.HasPrefix(runner.calls[i], want[i]) {
			t.Errorf("call %d = %q, want prefix %q", i, runner.calls[i], want[i])
		}
	}
	for _, call := range runner.calls[:2] {
		if strings.Contains(call, "quay-postgres.service") {
			t.Fatalf("PostgreSQL stopped before conversion: %v", runner.calls)
		}
	}
	partialPath := m.postgresPartialDBPath()
	for _, path := range []string{filepath.Join(m.DataDir, markerFile), partialPath, partialPath + "-wal", partialPath + "-shm"} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Errorf("rollback left migration artifact %s: %v", path, err)
		}
	}
	if _, err := os.Stat(filepath.Join(m.DataDir, "quay.db")); err != nil {
		t.Fatalf("rollback removed published target database: %v", err)
	}
}

func TestRemovePostgresMigrationArtifactsRetainsMarkerWhenRetryIsUnsafe(t *testing.T) {
	m := &Migrator{DataDir: t.TempDir()}
	partialPath := m.postgresPartialDBPath()
	markerPath := filepath.Join(m.DataDir, markerFile)
	configPath := filepath.Join(m.DataDir, runtimeConfigFile)
	for _, path := range []string{markerPath, partialPath, partialPath + "-wal", partialPath + "-shm", configPath} {
		if err := os.WriteFile(path, []byte("migration artifact"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	if err := m.removePostgresMigrationArtifacts(false); err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{markerPath, configPath} {
		if _, err := os.Stat(path); err != nil {
			t.Errorf("rollback removed fail-closed artifact %s: %v", path, err)
		}
	}
	for _, path := range []string{partialPath, partialPath + "-wal", partialPath + "-shm"} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Errorf("rollback left disposable artifact %s: %v", path, err)
		}
	}
}

func TestValidatePostgresBeforeStopRejectsResume(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	m := validInstallMigrator(t)
	m.Source.DatabaseKind = databasePostgres
	m.Source.SystemdScope = scopeUser
	if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(m.DataDir, markerFile), nil, 0o600); err != nil {
		t.Fatal(err)
	}
	err := m.validatePostgresBeforeStop(t.Context())
	if err == nil || !strings.Contains(err.Error(), "does not support resuming") {
		t.Fatalf("validatePostgresBeforeStop error = %v", err)
	}
}

func TestPostgresRejectsUncleanTargetDirBeforeStoppingOMR(t *testing.T) {
	for _, tc := range []struct {
		name      string
		fileNames []string
		wantErr   string
	}{
		{
			name:      "stale non-marker file",
			fileNames: []string{"quay.db.partial"},
			wantErr:   "target directory",
		},
		{
			name:      "corrupted leftovers",
			fileNames: []string{"some-stale-file.db", "storage"},
			wantErr:   "target directory",
		},
		{
			name:      "stale marker file",
			fileNames: []string{markerFile},
			wantErr:   "does not support resuming",
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("HOME", t.TempDir())
			m := validInstallMigrator(t)
			m.Source.DatabaseKind = databasePostgres
			m.Source.SystemdScope = scopeUser
			runner := &recordingRunner{}
			m.Runner = runner

			if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
				t.Fatal(err)
			}
			for _, name := range tc.fileNames {
				if err := os.WriteFile(filepath.Join(m.DataDir, name), []byte("stale"), 0o600); err != nil {
					t.Fatal(err)
				}
			}

			err := m.runPostgresMigration(t.Context())
			if err == nil || !strings.Contains(err.Error(), tc.wantErr) {
				t.Fatalf("runPostgresMigration error = %v, want substring %q", err, tc.wantErr)
			}
			if len(runner.runCalls) != 0 {
				t.Fatalf("OMR was touched before unclean target-dir rejection: %v", runner.runCalls)
			}
		})
	}
}

func TestPostgresRejectsExistingTargetQuadletBeforeStoppingOMR(t *testing.T) {
	m := validInstallMigrator(t)
	m.Source.DatabaseKind = databasePostgres
	m.Source.SystemdScope = scopeUser
	m.checkTargetInstallation = func() (bool, error) { return true, nil }
	runner := &recordingRunner{}
	m.Runner = runner

	err := m.runPostgresMigration(t.Context())
	if err == nil || !strings.Contains(err.Error(), "existing target Quay installation") {
		t.Fatalf("runPostgresMigration error = %v", err)
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("OMR was touched before target rejection: %v", runner.runCalls)
	}
}

func TestPostgresStopErrorStillRestoresOldServices(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	m := validInstallMigrator(t)
	m.Source.DatabaseKind = databasePostgres
	m.Source.SystemdScope = scopeUser
	runner := &sequenceRunner{appStopErr: errors.New("stop result unknown")}
	m.Runner = runner

	err := m.runPostgresMigration(t.Context())
	if err == nil || !strings.Contains(err.Error(), "stop result unknown") {
		t.Fatalf("runPostgresMigration error = %v", err)
	}
	want := []string{
		"systemctl --user stop quay-app.service",
		"systemctl --user start quay-pod.service",
		"systemctl --user start quay-postgres.service",
		"systemctl --user start quay-redis.service",
		"systemctl --user start quay-app.service",
	}
	if strings.Join(runner.calls, "\n") != strings.Join(want, "\n") {
		t.Fatalf("calls = %v, want %v", runner.calls, want)
	}
}

func TestPostgresUnsupportedFlags(t *testing.T) {
	for _, tc := range []struct {
		name string
		set  func(*Migrator)
		want string
	}{
		{name: "dry run", set: func(m *Migrator) { m.DryRun = true }, want: "-dry-run"},
		{name: "skip install", set: func(m *Migrator) { m.SkipInstall = true }, want: "-skip-install"},
		{name: "cleanup", set: func(m *Migrator) { m.Cleanup = true }, want: "-cleanup"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			m := &Migrator{}
			tc.set(m)
			err := m.validatePostgresFlags()
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("validatePostgresFlags error = %v, want %q", err, tc.want)
			}
		})
	}
}

func TestStopPostgresRemainingServicesAtCutover(t *testing.T) {
	runner := &recordingRunner{}
	m := &Migrator{Runner: runner, Source: OMRSource{SystemdScope: scopeSystem}}
	if err := m.stopPostgresRemainingServices(t.Context()); err != nil {
		t.Fatal(err)
	}
	want := []string{
		"systemctl stop quay-postgres.service",
		"systemctl stop quay-redis.service",
		"systemctl stop quay-pod.service",
	}
	if strings.Join(runner.runCalls, "\n") != strings.Join(want, "\n") {
		t.Fatalf("cutover calls = %v, want %v", runner.runCalls, want)
	}
}

func TestUpgradeSchemaAtomicallyPublishesPostgresIntermediate(t *testing.T) {
	dataDir := t.TempDir()
	partialPath := filepath.Join(dataDir, partialDatabaseName)
	db, err := dbcore.OpenSQLite(partialPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := dbcore.InitOMRSourceIntermediate(t.Context(), db); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	m := &Migrator{DataDir: dataDir, Out: &bytes.Buffer{}, Source: OMRSource{DatabaseKind: databasePostgres}}
	if err := m.upgradeSchema(t.Context()); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(partialPath); !os.IsNotExist(err) {
		t.Fatalf("partial database still exists: %v", err)
	}
	if backups, err := filepath.Glob(partialPath + ".backup-*"); err != nil || len(backups) != 0 {
		t.Fatalf("converted database backups = %v, err=%v", backups, err)
	}
	target, err := dbcore.OpenSQLiteReadOnly(filepath.Join(dataDir, "quay.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer target.Close()
	version, err := dbcore.SchemaVersion(t.Context(), target)
	if err != nil || version != dbcore.TargetVersion {
		t.Fatalf("published version = %q, err=%v", version, err)
	}
}

func TestUpgradeSchemaRejectsUnexpectedCurrentPostgresIntermediate(t *testing.T) {
	dataDir := t.TempDir()
	partialPath := filepath.Join(dataDir, partialDatabaseName)
	db, err := dbcore.OpenSQLite(partialPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := dbcore.InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	m := &Migrator{DataDir: dataDir, Out: &bytes.Buffer{}, Source: OMRSource{DatabaseKind: databasePostgres}}
	err = m.upgradeSchema(t.Context())
	if err == nil || !strings.Contains(err.Error(), "unexpectedly has target schema version") {
		t.Fatalf("upgradeSchema error = %v", err)
	}
	if _, err := os.Stat(partialPath); err != nil {
		t.Fatalf("unexpected intermediate was removed: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dataDir, "quay.db")); !os.IsNotExist(err) {
		t.Fatalf("unexpected intermediate was published: %v", err)
	}
}

type sequenceRunner struct {
	calls         []string
	namespaceErr  error
	namespaceHook func()
	appStopErr    error
}

func (r *sequenceRunner) Run(_ context.Context, name string, args ...string) error {
	call := name + " " + strings.Join(args, " ")
	r.calls = append(r.calls, call)
	if name == "podman" && len(args) > 0 && args[0] == "unshare" {
		if r.namespaceHook != nil {
			r.namespaceHook()
		}
		return r.namespaceErr
	}
	if strings.Contains(call, " stop quay-app.service") {
		return r.appStopErr
	}
	return nil
}

func (*sequenceRunner) Output(context.Context, string, ...string) (string, error) {
	return "", nil
}
