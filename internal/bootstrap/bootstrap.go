// Package bootstrap provides first-run initialization for the registry.
package bootstrap

import (
	"context"
	"crypto/rand"
	"database/sql"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
)

// AdminUser creates the initial admin user if no users exist in the database.
// It returns true if a user was created, false if users already exist.
// authDir is the directory where the admin-password file is stored.
func AdminUser(ctx context.Context, db *sql.DB, username, authDir string) (bool, error) {
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

	email := fmt.Sprintf("%s@localhost", username)
	if _, err := q.CreateAdminUser(ctx, daldb.CreateAdminUserParams{
		Uuid:         sql.NullString{String: uuid.NewString(), Valid: true},
		Username:     username,
		PasswordHash: sql.NullString{String: string(hash), Valid: true},
		Email:        email,
	}); err != nil {
		return false, fmt.Errorf("create user: %w", err)
	}

	slog.Info("admin user created", "username", username)
	slog.Info("password saved", "path", passFile)
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

	pass := rand.Text()

	if err := os.WriteFile(passFile, []byte(pass), 0o600); err != nil {
		return "", fmt.Errorf("write credentials file: %w", err)
	}

	return pass, nil
}
