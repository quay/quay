package migrate

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/credentials/encryptedfield"
	"gopkg.in/yaml.v3"
)

// validateSourceAuth checks only the authentication state that this migrator
// can preserve. It reads the source config and database without mutating them.
func (m *Migrator) validateSourceAuth(ctx context.Context, db *sql.DB) error {
	databaseSecretKey, err := m.validateSourceAuthConfig()
	if err != nil {
		return err
	}
	return validateRobotTokenContinuity(ctx, db, databaseSecretKey)
}

func (m *Migrator) validateSourceAuthConfig() (string, error) {
	if m.Source.ConfigDir == "" {
		return "", fmt.Errorf("source config directory not detected")
	}

	path := filepath.Join(m.Source.ConfigDir, runtimeConfigFile)
	raw, err := os.ReadFile(path) //nolint:gosec // source directory comes from detection or an explicit override
	if err != nil {
		return "", fmt.Errorf("read source config: %w", err)
	}

	var values map[string]any
	if err := yaml.Unmarshal(raw, &values); err != nil {
		return "", fmt.Errorf("parse source config: %w", err)
	}

	authType, err := requiredSourceConfigString(values, "AUTHENTICATION_TYPE")
	if err != nil {
		return "", err
	}
	if authType != "Database" {
		return "", fmt.Errorf("unsupported authentication provider %q: only Database is supported", authType)
	}

	if _, err := requiredSourceConfigString(values, "SERVER_HOSTNAME"); err != nil && m.Hostname == "" {
		return "", err
	}
	if _, err := requiredSourceConfigString(values, "SECRET_KEY"); err != nil {
		return "", err
	}
	databaseSecretKey, err := requiredSourceConfigString(values, "DATABASE_SECRET_KEY")
	if err != nil {
		return "", err
	}
	if _, err := encryptedfield.ConvertSecretKey(databaseSecretKey); err != nil {
		return "", fmt.Errorf("DATABASE_SECRET_KEY is not valid: %w", err)
	}
	return databaseSecretKey, nil
}

func requiredSourceConfigString(values map[string]any, field string) (string, error) {
	value, ok := values[field]
	if !ok {
		return "", fmt.Errorf("%s is missing from the source config", field)
	}
	text, ok := value.(string)
	if !ok || text == "" {
		return "", fmt.Errorf("%s must be a non-empty string in the source config", field)
	}
	return text, nil
}

// validateRobotTokenContinuity proves that populated robot tokens can still be
// decrypted by the target's Database authentication implementation.
func validateRobotTokenContinuity(ctx context.Context, db *sql.DB, databaseSecretKey string) error {
	rows, err := db.QueryContext(ctx, "SELECT token FROM robotaccounttoken WHERE token != ''")
	if err != nil {
		return fmt.Errorf("query robot tokens: %w", err)
	}
	defer func() { _ = rows.Close() }()

	for rows.Next() {
		var encryptedToken string
		if err := rows.Scan(&encryptedToken); err != nil {
			return fmt.Errorf("read robot token: %w", err)
		}
		if _, err := encryptedfield.Decrypt(databaseSecretKey, encryptedToken); err != nil {
			return fmt.Errorf("robot token cannot be decrypted with DATABASE_SECRET_KEY: %w", err)
		}
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("read robot tokens: %w", err)
	}
	return nil
}
