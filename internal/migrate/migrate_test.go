package migrate

import (
	"bytes"
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
