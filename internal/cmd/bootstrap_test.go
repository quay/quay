package cmd

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
)

func TestBootstrapDatabase_FreshDB(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := context.Background()
	if err := bootstrapDatabase(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}

	ver, err := dbcore.SchemaVersion(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if ver != dbcore.TargetVersion {
		t.Errorf("version = %q, want %q", ver, dbcore.TargetVersion)
	}
}

func TestBootstrapDatabase_ExistingDB(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := context.Background()
	if err := bootstrapDatabase(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}
	if err := bootstrapDatabase(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}
}

func TestBootstrapAdminUser_CreatesUser(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := context.Background()
	if err := dbcore.InitDatabase(ctx, db, os.Stderr); err != nil {
		t.Fatal(err)
	}

	authDir := filepath.Join(dir, "auth")
	created, err := bootstrapAdminUser(ctx, db, "admin", authDir)
	if err != nil {
		t.Fatal(err)
	}
	if !created {
		t.Error("expected user to be created")
	}

	q := daldb.New(db)
	user, err := q.GetUserByUsername(ctx, "admin")
	if err != nil {
		t.Fatal(err)
	}
	if !user.Enabled {
		t.Error("user should be enabled")
	}

	passFile := filepath.Join(authDir, "admin-password")
	data, err := os.ReadFile(passFile)
	if err != nil {
		t.Fatal(err)
	}
	if len(data) == 0 {
		t.Error("credentials file is empty")
	}

	info, _ := os.Stat(passFile)
	if info.Mode().Perm() != 0o600 {
		t.Errorf("permissions = %o, want 0600", info.Mode().Perm())
	}
}

func TestBootstrapAdminUser_SkipsExisting(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := context.Background()
	if err := dbcore.InitDatabase(ctx, db, os.Stderr); err != nil {
		t.Fatal(err)
	}

	authDir := filepath.Join(dir, "auth")
	if _, err := bootstrapAdminUser(ctx, db, "admin", authDir); err != nil {
		t.Fatal(err)
	}
	created, err := bootstrapAdminUser(ctx, db, "admin", authDir)
	if err != nil {
		t.Fatal(err)
	}
	if created {
		t.Error("should not create user when one already exists")
	}
}

func TestBootstrapAdminUser_ReadsPreSeededPassword(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := context.Background()
	if err := dbcore.InitDatabase(ctx, db, os.Stderr); err != nil {
		t.Fatal(err)
	}

	authDir := filepath.Join(dir, "auth")
	os.MkdirAll(authDir, 0o750)
	os.WriteFile(filepath.Join(authDir, "admin-password"), []byte("my-chosen-password"), 0o600)

	created, err := bootstrapAdminUser(ctx, db, "admin", authDir)
	if err != nil {
		t.Fatal(err)
	}
	if !created {
		t.Error("expected user to be created")
	}

	q := daldb.New(db)
	user, err := q.GetUserByUsername(ctx, "admin")
	if err != nil {
		t.Fatal(err)
	}
	if !user.PasswordHash.Valid {
		t.Error("password hash should be valid")
	}
}
