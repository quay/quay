package migrate

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestCleanup_RemovesUnitFiles(t *testing.T) {
	dir := t.TempDir()
	unitPath := filepath.Join(dir, "quay-app.service")
	os.WriteFile(unitPath, []byte("[Unit]\nDescription=test"), 0o644)

	m := &Migrator{
		Out: &bytes.Buffer{},
		Source: OMRSource{
			UnitFiles:    []string{unitPath},
			SystemdScope: "user",
		},
	}

	if err := m.removeUnitFiles(); err != nil {
		t.Fatalf("removeUnitFiles: %v", err)
	}

	if _, err := os.Stat(unitPath); !os.IsNotExist(err) {
		t.Error("unit file should have been removed")
	}
}

func TestCleanup_SkipsWhenNoUnits(t *testing.T) {
	m := &Migrator{
		Out:    &bytes.Buffer{},
		Source: OMRSource{},
	}

	if err := m.removeUnitFiles(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
