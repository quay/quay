package migrate

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/quay/quay/internal/dal/dbcore"
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
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "3f8d7acdf7f9"); err != nil {
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
	if revision != "3f8d7acdf7f9" {
		t.Errorf("source revision = %q, want unchanged approved revision", revision)
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
