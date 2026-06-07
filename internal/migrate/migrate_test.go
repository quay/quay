package migrate

import (
	"bytes"
	"strings"
	"testing"
)

func TestMigrator_Run_DryRun(t *testing.T) {
	m := &Migrator{
		DataDir: t.TempDir(),
		DryRun:  true,
		Out:     &bytes.Buffer{},
	}
	m.Source = OMRSource{
		ConfigDir:   "/fake/config",
		DBPath:      "/fake/db.db",
		StoragePath: "/fake/storage",
		Hostname:    "localhost",
		Method:      "test",
	}

	err := m.Run(t.Context())
	if err != nil {
		t.Fatalf("dry-run should not error with pre-set source: %v", err)
	}

	out := m.Out.(*bytes.Buffer).String()
	if out == "" {
		t.Error("expected dry-run output")
	}
}

func TestMigrator_Run_DryRunWithManualSourceSkipsDetection(t *testing.T) {
	var out bytes.Buffer
	m := &Migrator{
		DataDir:       t.TempDir(),
		SourceDB:      "/manual/quay_sqlite.db",
		SourceStorage: "/manual/storage",
		SourceCerts:   "/manual/config",
		Hostname:      "registry.example.com",
		DryRun:        true,
		Out:           &out,
	}

	if err := m.Run(t.Context()); err != nil {
		t.Fatalf("dry-run should not auto-detect with manual source: %v", err)
	}

	got := out.String()
	for _, want := range []string{
		"via manual",
		"/manual/quay_sqlite.db",
		"/manual/storage",
		"/manual/config",
		"registry.example.com",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("dry-run output missing %q: %s", want, got)
		}
	}
}
