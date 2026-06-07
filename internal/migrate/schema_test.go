package migrate

import (
	"bytes"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/dal/dbcore"
)

func TestUpgradeSchema_AlreadyCurrent(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay.db")

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	if err := dbcore.InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	db.Close()

	m := &Migrator{
		DataDir: dir,
		Out:     &bytes.Buffer{},
	}

	if err := m.upgradeSchema(t.Context()); err != nil {
		t.Fatalf("upgradeSchema: %v", err)
	}
}
