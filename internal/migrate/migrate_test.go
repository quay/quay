package migrate

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/installer"
)

func TestMigrator_Run_DryRunValidatesApprovedSourceWithoutMutation(t *testing.T) {
	m := validInstallMigrator(t)
	m.DryRun = true
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &recordingRunner{}
	m.Runner = runner

	db, err := dbcore.OpenSQLite(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", dbcore.ApprovedOMRSourceVersion); err != nil {
		t.Fatalf("stamp approved revision: %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	if err := m.Run(t.Context()); err != nil {
		t.Fatalf("Run: %v", err)
	}
	if m.Out.(*bytes.Buffer).Len() == 0 {
		t.Fatal("dry-run did not print a plan")
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("dry-run stopped source services: %v", runner.runCalls)
	}
	entries, err := os.ReadDir(m.DataDir)
	if err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("dry-run modified target directory: %v", entries)
	}

	readOnly, err := dbcore.OpenSQLiteReadOnly(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	defer readOnly.Close()
	revision, err := dbcore.SchemaVersion(t.Context(), readOnly)
	if err != nil {
		t.Fatal(err)
	}
	if revision != dbcore.ApprovedOMRSourceVersion {
		t.Errorf("source revision = %q, want unchanged approved revision", revision)
	}
}

func TestMigrator_Run_DryRunTakesPrecedenceOverCleanupAndSkipInstall(t *testing.T) {
	for _, tc := range []struct {
		name        string
		cleanup     bool
		skipInstall bool
	}{
		{name: "cleanup", cleanup: true},
		{name: "skip-install", skipInstall: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			m := validInstallMigrator(t)
			m.DryRun = true
			m.Cleanup = tc.cleanup
			m.SkipInstall = tc.skipInstall
			unitFile := filepath.Join(t.TempDir(), "quay-app.service")
			if err := os.WriteFile(unitFile, nil, 0o600); err != nil {
				t.Fatal(err)
			}
			m.Source.UnitFiles = []string{unitFile}
			runner := &recordingRunner{}
			m.Runner = runner

			if err := m.Run(t.Context()); err != nil {
				t.Fatalf("Run: %v", err)
			}
			if !strings.Contains(m.Out.(*bytes.Buffer).String(), "Detected OMR installation") {
				t.Fatalf("dry-run did not print a plan: %q", m.Out.(*bytes.Buffer).String())
			}
			if len(runner.runCalls) != 0 {
				t.Fatalf("dry-run ran commands: %v", runner.runCalls)
			}
			if _, err := os.Stat(unitFile); err != nil {
				t.Fatalf("dry-run removed unit file: %v", err)
			}
			entries, err := os.ReadDir(m.DataDir)
			if err != nil && !os.IsNotExist(err) {
				t.Fatal(err)
			}
			if len(entries) != 0 {
				t.Fatalf("dry-run modified target directory: %v", entries)
			}
		})
	}
}

func TestMigrator_Run_DryRunRejectsForwardStampedMinimalSchema(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay_sqlite.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		"CREATE TABLE alembic_version (version_num TEXT NOT NULL)",
		"INSERT INTO alembic_version VALUES ('" + dbcore.TargetVersion + "')",
		"CREATE TABLE robotaccounttoken (token TEXT NOT NULL)",
	} {
		if _, err := db.ExecContext(t.Context(), statement); err != nil {
			t.Fatalf("create minimal source schema: %v", err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	configDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(configDir, runtimeConfigFile), []byte("AUTHENTICATION_TYPE: Database\nSERVER_HOSTNAME: registry.example.com\nSECRET_KEY: test-secret\nDATABASE_SECRET_KEY: test1234\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	var out bytes.Buffer
	runner := &recordingRunner{}
	m := &Migrator{
		DataDir: t.TempDir() + "/target",
		DryRun:  true,
		Out:     &out,
		Runner:  runner,
		Source: OMRSource{
			ConfigDir: configDir,
			DBPath:    dbPath,
			Hostname:  "registry.example.com",
			Image:     "quay.io/quay/quay-mirror:test",
			UnitFiles: []string{"/etc/systemd/system/quay-app.service"},
		},
	}

	err = m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "unsupported OMR source revision") {
		t.Fatalf("Run error = %v, want forward-stamped schema rejection", err)
	}
	if out.Len() != 0 {
		t.Fatalf("dry-run printed a plan after forward-stamped source rejection: %s", out.String())
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("source services were stopped before source rejection: %v", runner.runCalls)
	}

	readOnly, err := dbcore.OpenSQLiteReadOnly(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer readOnly.Close()
	revision, err := dbcore.SchemaVersion(t.Context(), readOnly)
	if err != nil {
		t.Fatal(err)
	}
	if revision != dbcore.TargetVersion {
		t.Errorf("source revision = %q, want unchanged forward stamp %q", revision, dbcore.TargetVersion)
	}
}

func TestMigrator_Run_DryRunRejectsUnsupportedRevision(t *testing.T) {
	m := validInstallMigrator(t)
	m.DryRun = true
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &recordingRunner{}
	m.Runner = runner

	db, err := dbcore.OpenSQLite(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "0cdd1f27a450"); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	err = m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "unsupported OMR source revision") {
		t.Fatalf("Run error = %v, want unsupported revision", err)
	}
	if m.Out.(*bytes.Buffer).Len() != 0 {
		t.Fatalf("dry-run printed a plan after rejected source: %s", m.Out.(*bytes.Buffer).String())
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("dry-run stopped source services: %v", runner.runCalls)
	}

	readOnly, err := dbcore.OpenSQLiteReadOnly(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	defer readOnly.Close()
	revision, err := dbcore.SchemaVersion(t.Context(), readOnly)
	if err != nil {
		t.Fatal(err)
	}
	if revision != "0cdd1f27a450" {
		t.Errorf("source revision = %q, want unchanged unsupported revision", revision)
	}
}

func TestMigrator_Run_DryRunRejectsUnsupportedAuthentication(t *testing.T) {
	m := validInstallMigrator(t)
	m.DryRun = true
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &recordingRunner{}
	m.Runner = runner

	configPath := filepath.Join(m.Source.ConfigDir, runtimeConfigFile)
	configData, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	configData = []byte(strings.Replace(string(configData), "AUTHENTICATION_TYPE: Database", "AUTHENTICATION_TYPE: LDAP", 1))
	if err := os.WriteFile(configPath, configData, 0o600); err != nil {
		t.Fatal(err)
	}

	err = m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "unsupported authentication provider") {
		t.Fatalf("Run error = %v, want unsupported authentication provider", err)
	}
	if m.Out.(*bytes.Buffer).Len() != 0 {
		t.Fatalf("dry-run printed a plan after rejected authentication: %s", m.Out.(*bytes.Buffer).String())
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("dry-run stopped source services: %v", runner.runCalls)
	}
}

func TestMigrator_RunSQLiteCopyFailureRestartsSourceServices(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &recordingRunner{}
	m.Runner = runner
	// A dangling link passes storage validation but fails the copy.
	if err := os.Symlink(filepath.Join(t.TempDir(), "missing"), filepath.Join(m.Source.StoragePath, "sha256", "ab", "blob")); err != nil {
		t.Fatal(err)
	}

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "copy storage") {
		t.Fatalf("Run error = %v, want copy storage failure", err)
	}
	want := []string{
		"systemctl stop quay-app.service",
		"systemctl stop quay-redis.service",
		"systemctl stop quay-pod.service",
		"systemctl start quay-pod.service",
		"systemctl start quay-redis.service",
		"systemctl start quay-app.service",
	}
	if strings.Join(runner.runCalls, "\n") != strings.Join(want, "\n") {
		t.Fatalf("calls = %v, want %v", runner.runCalls, want)
	}
}

func TestMigrator_RunSQLiteRetryAfterInjectedFailureResumes(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.UnitFiles = []string{filepath.Join(t.TempDir(), "quay-app.service")}
	m.Runner = &recordingRunner{}
	m.checkTargetInstallation = func() (bool, error) { return false, nil }
	t.Setenv(failAtEnv, "after-copy")

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "injected failure at after-copy") || !strings.Contains(err.Error(), "old OMR services restarted") {
		t.Fatalf("Run error = %v, want injected failure with restart", err)
	}
	if _, err := os.Stat(filepath.Join(m.DataDir, markerFile)); err != nil {
		t.Fatalf("failed copy lost its migration marker: %v", err)
	}

	// With -cleanup, a marked target must resume the migration, not skip to cleanup.
	t.Setenv(failAtEnv, "")
	m.Cleanup = true
	runner := &recordingRunner{}
	m.Runner = runner
	if err := m.Run(t.Context()); err != nil {
		t.Fatalf("retry: %v", err)
	}
	if len(runner.runCalls) == 0 || runner.runCalls[0] != "systemctl stop quay-app.service" {
		t.Fatalf("retry did not rerun the migration: %v", runner.runCalls)
	}
	db, err := dbcore.OpenSQLiteReadOnly(filepath.Join(m.DataDir, "quay.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	revision, err := dbcore.SchemaVersion(t.Context(), db)
	if err != nil {
		t.Fatal(err)
	}
	if revision != dbcore.TargetVersion {
		t.Errorf("target revision = %q, want %q", revision, dbcore.TargetVersion)
	}
}

func TestMigrator_RunSQLiteRollbackReportsFailedRestart(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &recordingRunner{runErrs: map[string]error{"quay-redis.service": errors.New("unit failed")}}
	m.Runner = runner
	t.Setenv(failAtEnv, "after-schema")

	err := m.Run(t.Context())
	if err == nil {
		t.Fatal("Run succeeded, want injected failure")
	}
	for _, want := range []string{"injected failure at after-schema", "rollback old OMR", "start quay-redis.service: unit failed"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("Run error = %v, want %q", err, want)
		}
	}
	if strings.Contains(err.Error(), "restarted") {
		t.Errorf("Run error = %v, claims a restart that failed", err)
	}
	starts := runner.runCalls[len(runner.runCalls)-3:]
	want := []string{"systemctl start quay-pod.service", "systemctl start quay-redis.service", "systemctl start quay-app.service"}
	if strings.Join(starts, "\n") != strings.Join(want, "\n") {
		t.Fatalf("rollback calls = %v, want %v", starts, want)
	}
}

func TestMigrator_RunSQLiteCleanupAfterSkipInstallDoesNotRecopy(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.UnitFiles = []string{filepath.Join(t.TempDir(), "quay-app.service")}
	m.Runner = &recordingRunner{}
	if err := m.Run(t.Context()); err != nil {
		t.Fatalf("skip-install run: %v", err)
	}

	// The user installs by hand between the two runs; cleanup must keep that database.
	dbPath := filepath.Join(m.DataDir, "quay.db")
	if err := os.WriteFile(dbPath, []byte("installed by hand"), 0o600); err != nil {
		t.Fatal(err)
	}
	m.SkipInstall = false
	m.Cleanup = true
	runner := &recordingRunner{}
	m.Runner = runner
	err := m.Run(t.Context())
	for _, call := range runner.runCalls {
		if strings.Contains(call, " stop ") {
			t.Errorf("cleanup reran the migration: %v", runner.runCalls)
			break
		}
	}
	if got, readErr := os.ReadFile(dbPath); readErr != nil || string(got) != "installed by hand" {
		t.Errorf("cleanup replaced the installed quay.db (read error %v)", readErr)
	}
	if err != nil {
		t.Fatalf("cleanup run: %v", err)
	}
}

func TestMigrator_RunSQLiteSkipInstallReportsStuckMarker(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.UnitFiles = []string{filepath.Join(t.TempDir(), "quay-app.service")}
	m.Runner = &recordingRunner{}
	// The checkpoint runs after the marker is written; a non-empty directory
	// in its place makes the final removal fail.
	m.Checkpoint = func(ctx context.Context, dbPath string) error {
		markerPath := filepath.Join(m.DataDir, markerFile)
		if err := os.Remove(markerPath); err != nil {
			return err
		}
		if err := os.MkdirAll(filepath.Join(markerPath, "stuck"), 0o750); err != nil {
			return err
		}
		return checkpointSQLite(ctx, dbPath)
	}

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "remove migration marker") {
		t.Fatalf("Run error = %v, want remove migration marker failure", err)
	}
}

func TestMigrator_RunSQLiteValidateFailureDoesNotRestart(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.DBPath = filepath.Join(t.TempDir(), "missing.db")
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &recordingRunner{}
	m.Runner = runner

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "validate") {
		t.Fatalf("Run error = %v, want validate failure", err)
	}
	if strings.Contains(err.Error(), "restarted") {
		t.Errorf("Run error = %v, claims a restart before the stop", err)
	}
	for _, call := range runner.runCalls {
		if strings.Contains(call, " start ") {
			t.Fatalf("failure before the stop started old OMR services: %v", runner.runCalls)
		}
	}
}

func TestMigrator_RunSQLiteInstallFailureRemovesOnlyOwnedInstall(t *testing.T) {
	for _, tc := range []struct {
		name        string
		existed     bool
		wantRemoved bool
	}{
		{name: "pre-existing install is kept", existed: true, wantRemoved: false},
		{name: "install created by this run is removed", existed: false, wantRemoved: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("HOME", t.TempDir())
			m := validInstallMigrator(t)
			m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
			runner := &recordingRunner{}
			m.Runner = runner
			m.checkTargetInstallation = func() (bool, error) { return tc.existed, nil }
			removed := false
			m.removeTargetInstall = func(context.Context) error {
				removed = true
				return nil
			}
			m.runInstall = func(context.Context, *installer.Config) error {
				return errors.New("injected install failure")
			}

			err := m.Run(t.Context())
			if err == nil || !strings.Contains(err.Error(), "install: ") || !strings.Contains(err.Error(), "old OMR services restarted") {
				t.Fatalf("Run error = %v, want install failure with restart", err)
			}
			if removed != tc.wantRemoved {
				t.Errorf("target install removed = %v, want %v", removed, tc.wantRemoved)
			}
			starts := runner.runCalls[len(runner.runCalls)-3:]
			want := []string{"systemctl start quay-pod.service", "systemctl start quay-redis.service", "systemctl start quay-app.service"}
			if strings.Join(starts, "\n") != strings.Join(want, "\n") {
				t.Fatalf("rollback calls = %v, want %v", starts, want)
			}
		})
	}
}

// slowRollbackRunner holds one source start until its context ends and records
// the context state quay-app.service was started with.
type slowRollbackRunner struct {
	recordingRunner
	slowStart  string
	appStarted bool
	appCtxErr  error
}

func (r *slowRollbackRunner) Run(ctx context.Context, name string, args ...string) error {
	err := r.recordingRunner.Run(ctx, name, args...)
	if len(args) < 2 || args[len(args)-2] != "start" {
		return err
	}
	switch args[len(args)-1] {
	case r.slowStart:
		<-ctx.Done()
		return ctx.Err()
	case quayAppUnit:
		r.appStarted = true
		r.appCtxErr = ctx.Err()
	}
	return err
}

func TestMigrator_RunSQLiteRollbackGivesEachStepItsOwnTimeout(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	original := rollbackStepTimeout
	rollbackStepTimeout = 50 * time.Millisecond
	t.Cleanup(func() { rollbackStepTimeout = original })

	m := validInstallMigrator(t)
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	runner := &slowRollbackRunner{slowStart: quayPodUnit}
	m.Runner = runner
	m.checkTargetInstallation = func() (bool, error) { return false, nil }
	m.removeTargetInstall = func(ctx context.Context) error {
		<-ctx.Done()
		return ctx.Err()
	}
	m.runInstall = func(context.Context, *installer.Config) error {
		return errors.New("injected install failure")
	}

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "start quay-pod.service") {
		t.Fatalf("Run error = %v, want slow quay-pod restart reported", err)
	}
	if !runner.appStarted || runner.appCtxErr != nil {
		t.Fatalf("quay-app restart started = %v with context error %v, want a live context", runner.appStarted, runner.appCtxErr)
	}
}

// containerKeyRunner serves source key material from the old OMR container.
type containerKeyRunner struct {
	recordingRunner
	material sourceMaterialRunner
}

func (r *containerKeyRunner) Output(ctx context.Context, name string, args ...string) (string, error) {
	return r.material.Output(ctx, name, args...)
}

func TestMigrator_RunSQLiteValidateFailureRemovesRecoveredKeyMaterial(t *testing.T) {
	m := validInstallMigrator(t)
	m.SkipInstall = true
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
	outputs := map[string]string{}
	for _, name := range []string{legacyPrivateKeyName, legacyKeyIDName} {
		path := filepath.Join(m.Source.ConfigDir, name)
		data, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.Remove(path); err != nil {
			t.Fatal(err)
		}
		outputs[filepath.Join(sourceContainerConf, name)] = string(data)
	}
	runner := &containerKeyRunner{material: sourceMaterialRunner{outputs: outputs}}
	m.Runner = runner
	// A non-empty target fails validation after the key material is recovered.
	if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(m.DataDir, "unrelated"), nil, 0o600); err != nil {
		t.Fatal(err)
	}

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "is not empty") {
		t.Fatalf("Run error = %v, want non-empty target rejection", err)
	}
	if runner.material.outputCalls == 0 {
		t.Fatal("key material was not recovered from the source container")
	}
	for _, name := range []string{legacyPrivateKeyName, legacyKeyIDName} {
		if _, err := os.Stat(filepath.Join(m.Source.ConfigDir, name)); !os.IsNotExist(err) {
			t.Errorf("recovered %s left in source config dir: %v", name, err)
		}
	}
	if len(runner.runCalls) != 0 {
		t.Errorf("failure before the stop ran source services: %v", runner.runCalls)
	}
}

func TestMigrator_Run_DryRunLeavesSourceKeyMaterialAsFound(t *testing.T) {
	for _, tc := range []struct {
		name      string
		recovered bool
		failValid bool
	}{
		{name: "recovered key, success", recovered: true},
		{name: "recovered key, validate failure", recovered: true, failValid: true},
		{name: "host key, success"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			m := validInstallMigrator(t)
			m.DryRun = true
			m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}
			outputs := map[string]string{}
			if tc.recovered {
				for _, name := range []string{legacyPrivateKeyName, legacyKeyIDName} {
					path := filepath.Join(m.Source.ConfigDir, name)
					data, err := os.ReadFile(path)
					if err != nil {
						t.Fatal(err)
					}
					if err := os.Remove(path); err != nil {
						t.Fatal(err)
					}
					outputs[filepath.Join(sourceContainerConf, name)] = string(data)
				}
			}
			runner := &containerKeyRunner{material: sourceMaterialRunner{outputs: outputs}}
			m.Runner = runner
			if tc.failValid {
				// A non-empty target fails validation after the key material is recovered.
				if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(filepath.Join(m.DataDir, "unrelated"), nil, 0o600); err != nil {
					t.Fatal(err)
				}
			}

			err := m.Run(t.Context())
			if tc.failValid {
				if err == nil || !strings.Contains(err.Error(), "is not empty") {
					t.Fatalf("Run error = %v, want non-empty target rejection", err)
				}
			} else if err != nil {
				t.Fatalf("Run: %v", err)
			}
			if tc.recovered && runner.material.outputCalls == 0 {
				t.Fatal("key material was not recovered from the source container")
			}
			for _, name := range []string{legacyPrivateKeyName, legacyKeyIDName} {
				_, err := os.Stat(filepath.Join(m.Source.ConfigDir, name))
				if tc.recovered && !os.IsNotExist(err) {
					t.Errorf("dry-run left recovered %s in source config dir: %v", name, err)
				}
				if !tc.recovered && err != nil {
					t.Errorf("dry-run removed pre-existing %s: %v", name, err)
				}
			}
		})
	}
}

func TestMigrator_RunSQLiteCleanupRefusesResumeOverCompletedInstall(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	m := validInstallMigrator(t)
	m.Source.UnitFiles = []string{filepath.Join(t.TempDir(), "quay-app.service")}
	m.Runner = &recordingRunner{}
	installed := false
	m.checkTargetInstallation = func() (bool, error) { return installed, nil }
	m.runInstall = func(context.Context, *installer.Config) error {
		installed = true
		return nil
	}
	if err := m.Run(t.Context()); err != nil {
		t.Fatalf("migration: %v", err)
	}

	// The install finished but its marker survived, as after a crash before
	// the marker removal; the new registry has since written its database.
	if err := os.WriteFile(filepath.Join(m.DataDir, markerFile), []byte("migration in progress\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	dbPath := filepath.Join(m.DataDir, "quay.db")
	if err := os.WriteFile(dbPath, []byte("live v3 data"), 0o600); err != nil {
		t.Fatal(err)
	}
	m.Cleanup = true
	runner := &recordingRunner{}
	m.Runner = runner

	err := m.Run(t.Context())
	if err == nil || !strings.Contains(err.Error(), "refusing to resume") {
		t.Fatalf("Run error = %v, want refusal to resume over the installed target", err)
	}
	if len(runner.runCalls) != 0 {
		t.Errorf("refused resume ran source services: %v", runner.runCalls)
	}
	if got, readErr := os.ReadFile(dbPath); readErr != nil || string(got) != "live v3 data" {
		t.Errorf("refused resume replaced the installed quay.db (read error %v)", readErr)
	}
}
