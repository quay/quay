package bootstrap

import (
	"io"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
	"golang.org/x/crypto/bcrypt"
)

func TestAdminUser_CreatesUser(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := dbcore.InitDatabase(ctx, db, io.Discard); err != nil {
		t.Fatal(err)
	}

	created, err := AdminUser(ctx, db, "admin", "my-chosen-password")
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
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash.String), []byte("my-chosen-password")); err != nil {
		t.Errorf("password does not match stored hash: %v", err)
	}
}

func TestAdminUser_SkipsExisting(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := dbcore.InitDatabase(ctx, db, io.Discard); err != nil {
		t.Fatal(err)
	}

	if _, err := AdminUser(ctx, db, "admin", "first-password"); err != nil {
		t.Fatal(err)
	}
	created, err := AdminUser(ctx, db, "other", "second-password")
	if err != nil {
		t.Fatal(err)
	}
	if created {
		t.Error("should not create user when one already exists")
	}
}

func TestRequireAdminUser(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := dbcore.InitDatabase(ctx, db, io.Discard); err != nil {
		t.Fatal(err)
	}

	if _, err := RequireAdminUser(ctx, db); err == nil {
		t.Fatal("expected an uninitialized database error")
	}

	created, err := AdminUser(ctx, db, "custom-admin", "my-chosen-password")
	if err != nil {
		t.Fatal(err)
	}
	if !created {
		t.Error("expected user to be created")
	}

	username, err := RequireAdminUser(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if username != "custom-admin" {
		t.Errorf("username = %q, want custom-admin", username)
	}
}
