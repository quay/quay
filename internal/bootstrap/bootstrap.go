// Package bootstrap provides first-run initialization for the registry.
package bootstrap

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
)

// HasUsers reports whether the database already contains a login user.
func HasUsers(ctx context.Context, db *sql.DB) (bool, error) {
	q := daldb.New(db)
	count, err := q.CountUsers(ctx)
	if err != nil {
		return false, fmt.Errorf("count users: %w", err)
	}
	return count > 0, nil
}

// RequireAdminUser verifies that install-time provisioning has created a user
// and returns the first login username for standalone default authorization.
func RequireAdminUser(ctx context.Context, db *sql.DB) (string, error) {
	var username string
	err := db.QueryRowContext(ctx, `
		SELECT username FROM "user"
		WHERE organization = 0 AND robot = 0
		ORDER BY id LIMIT 1
	`).Scan(&username)
	if err != nil {
		if err == sql.ErrNoRows {
			return "", fmt.Errorf("database has no users; run `quay init` or `quay install` to provision the initial administrator")
		}
		return "", fmt.Errorf("find initial administrator: %w", err)
	}
	return username, nil
}

// AdminUser creates the initial admin user if no users exist in the database.
// It returns true if a user was created, false if users already exist. Password
// generation and persistence belong to the one-shot installer, not the server.
func AdminUser(ctx context.Context, db *sql.DB, username, password string) (bool, error) {
	q := daldb.New(db)

	hasUsers, err := HasUsers(ctx, db)
	if err != nil {
		return false, err
	}
	if hasUsers {
		return false, nil
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
	return true, nil
}
