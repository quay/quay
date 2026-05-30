package cmd

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
)

func bootstrapDatabase(ctx context.Context, db *sql.DB, dbPath string) error {
	var tableCount int
	err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount)
	if err != nil {
		return fmt.Errorf("check tables: %w", err)
	}

	if tableCount == 0 {
		fmt.Fprintln(os.Stderr, "initializing database...")
		if err := dbcore.InitDatabase(ctx, db, os.Stderr); err != nil {
			return fmt.Errorf("init database: %w", err)
		}
		return nil
	}

	ver, err := dbcore.SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("schema version: %w", err)
	}

	if ver == dbcore.TargetVersion {
		return nil
	}

	fmt.Fprintf(os.Stderr, "upgrading database from %s to %s\n", ver, dbcore.TargetVersion)

	backupPath, err := dbcore.BackupDatabase(ctx, db, dbPath)
	if err != nil {
		return fmt.Errorf("backup: %w", err)
	}
	fmt.Fprintf(os.Stderr, "backup: %s\n", backupPath)

	if err := dbcore.ApplyMigrations(ctx, db, ver, dbcore.TargetVersion, os.Stderr); err != nil {
		return fmt.Errorf("migrate (restore from %s): %w", backupPath, err)
	}

	_ = dbcore.CleanOldBackups(dbPath, 3)
	return nil
}

func bootstrapAdminUser(ctx context.Context, db *sql.DB, username, authDir string) (bool, error) {
	q := daldb.New(db)

	count, err := q.CountUsers(ctx)
	if err != nil {
		return false, fmt.Errorf("count users: %w", err)
	}
	if count > 0 {
		return false, nil
	}

	if err := os.MkdirAll(authDir, 0o750); err != nil {
		return false, fmt.Errorf("create auth dir: %w", err)
	}

	passFile := filepath.Join(authDir, "admin-password")
	password, err := readOrGeneratePassword(passFile)
	if err != nil {
		return false, fmt.Errorf("password: %w", err)
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return false, fmt.Errorf("hash password: %w", err)
	}

	uuid, err := generateUUID()
	if err != nil {
		return false, fmt.Errorf("generate UUID: %w", err)
	}

	email := fmt.Sprintf("%s@localhost", username)
	if _, err := q.CreateAdminUser(ctx, daldb.CreateAdminUserParams{
		Uuid:         sql.NullString{String: uuid, Valid: true},
		Username:     username,
		PasswordHash: sql.NullString{String: string(hash), Valid: true},
		Email:        email,
	}); err != nil {
		return false, fmt.Errorf("create user: %w", err)
	}

	fmt.Fprintf(os.Stderr, "admin credentials: %s / %s\n", username, password)
	fmt.Fprintf(os.Stderr, "credentials saved to: %s\n", passFile)
	return true, nil
}

func readOrGeneratePassword(passFile string) (string, error) {
	data, err := os.ReadFile(passFile) //nolint:gosec // known path in data dir
	if err == nil {
		pass := strings.TrimSpace(string(data))
		if pass != "" {
			return pass, nil
		}
	}

	pass, err := generatePassword(32)
	if err != nil {
		return "", err
	}

	if err := os.WriteFile(passFile, []byte(pass), 0o600); err != nil {
		return "", fmt.Errorf("write credentials file: %w", err)
	}

	return pass, nil
}
