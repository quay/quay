package migrate

import (
	"context"
	"crypto/rsa"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-jose/go-jose/v4"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/registry/jwtauth"
	"github.com/quay/quay/internal/system"
)

const (
	legacyPrivateKeyName = "quay.pem"
	legacyKeyIDName      = "quay.kid"
	sourceContainerName  = "quay-app"
	sourceContainerConf  = "/quay-registry/conf"
)

func (m *Migrator) importRegistryJWTSigningKey(ctx context.Context, targetDBPath string, sourceCfg *config.Config, replace bool) error {
	key := m.sourceRegistryJWTKey
	if key == nil {
		var err error
		key, _, err = loadApprovedRegistryJWTSigningKey(ctx, targetDBPath, m.Source.ConfigDir, sourceCfg, m.Runner, &m.persistedConfigFiles)
		if err != nil {
			return err
		}
	}
	targetPath := filepath.Join(m.DataDir, jwtauth.KeyFileName)
	existing, err := jwtauth.LoadPrivateKey(targetPath)
	if err == nil {
		if !jwtauth.PublicKeysEqual(&existing.PublicKey, &key.PublicKey) {
			if !replace {
				return fmt.Errorf("existing native registry JWT key does not match the approved source key")
			}
			slog.Warn("replacing mismatched target registry JWT signing key during migration resume", "path", targetPath)
			if err := jwtauth.ReplacePrivateKey(targetPath, key); err != nil {
				return fmt.Errorf("replace source registry JWT key during resume: %w", err)
			}
		}
		return nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	if err := jwtauth.WritePrivateKey(targetPath, key); err != nil {
		return fmt.Errorf("import source registry JWT key: %w", err)
	}
	return nil
}

func loadApprovedRegistryJWTSigningKey(ctx context.Context, dbPath, configDir string, cfg *config.Config, runner system.CommandRunner, persisted *[]string) (*rsa.PrivateKey, string, error) {
	key, kid, err := loadRegistryJWTSigningKey(ctx, configDir, cfg, runner, persisted)
	if err != nil {
		return nil, "", err
	}
	if err := validateRegistryJWTSigningKey(ctx, dbPath, cfg, key, kid); err != nil {
		return nil, "", err
	}
	return key, kid, nil
}

func loadRegistryJWTSigningKey(ctx context.Context, configDir string, cfg *config.Config, runner system.CommandRunner, persisted *[]string) (*rsa.PrivateKey, string, error) {
	privateBytes, privateSource, err := readSourceConfigMaterial(
		ctx, configDir, cfg.InstanceServiceKeyLocation, legacyPrivateKeyName, runner, persisted,
	)
	if err != nil {
		return nil, "", fmt.Errorf("load source registry JWT private key: %w", err)
	}
	key, err := jwtauth.ParsePrivateKey(privateBytes)
	if err != nil {
		return nil, "", fmt.Errorf("parse source registry JWT private key from %s: %w", privateSource, err)
	}
	kidBytes, kidSource, err := readSourceConfigMaterial(
		ctx, configDir, cfg.InstanceServiceKeyKIDLocation, legacyKeyIDName, runner, persisted,
	)
	if err != nil {
		return nil, "", fmt.Errorf("read source registry JWT key ID: %w", err)
	}
	kid := strings.TrimSpace(string(kidBytes))
	if kid == "" {
		return nil, "", fmt.Errorf("source registry JWT key ID from %s is empty", kidSource)
	}
	derivedKID, err := jwtauth.KeyID(&key.PublicKey)
	if err != nil {
		return nil, "", err
	}
	if derivedKID != kid {
		return nil, "", fmt.Errorf("source registry JWT private key does not match key ID %q", kid)
	}
	return key, kid, nil
}

func validateRegistryJWTSigningKey(ctx context.Context, dbPath string, cfg *config.Config, key *rsa.PrivateKey, kid string) error {
	db, err := dbcore.OpenSQLiteReadOnly(dbPath)
	if err != nil {
		return fmt.Errorf("open source database for registry JWT key validation: %w", err)
	}
	defer func() { _ = db.Close() }()
	var rawJWK string
	err = db.QueryRowContext(ctx, `
		SELECT sk.jwk
		FROM servicekey AS sk
		JOIN servicekeyapproval AS approval ON approval.id = sk.approval_id
		WHERE sk.kid = ? AND sk.service = ?
		  AND (sk.expiration_date IS NULL OR julianday(sk.expiration_date) > julianday('now'))
	`, kid, cfg.InstanceServiceKeyService).Scan(&rawJWK)
	if errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("source registry JWT key %q is not approved and unexpired for service %q", kid, cfg.InstanceServiceKeyService)
	}
	if err != nil {
		return fmt.Errorf("query approved source registry JWT key: %w", err)
	}
	var jwk jose.JSONWebKey
	if err := json.Unmarshal([]byte(rawJWK), &jwk); err != nil {
		return fmt.Errorf("parse approved source registry JWT JWK: %w", err)
	}
	if jwk.KeyID != "" && jwk.KeyID != kid {
		return fmt.Errorf("approved source registry JWT JWK has mismatched key ID %q", jwk.KeyID)
	}
	publicJWK := jwk.Public()
	if !jwtauth.PublicKeysEqual(&key.PublicKey, publicJWK.Key) {
		return fmt.Errorf("source registry JWT private key does not match approved database JWK")
	}
	return nil
}

// readSourceConfigMaterial appends each file it writes into the source config
// dir to persisted, so a rollback can return that dir to the old OMR as found.
func readSourceConfigMaterial(
	ctx context.Context,
	configDir, configured, defaultName string,
	runner system.CommandRunner,
	persisted *[]string,
) (material []byte, source string, readErr error) {
	hostPath, containerPath := sourceConfigPaths(configDir, configured, defaultName)
	data, err := os.ReadFile(hostPath) //nolint:gosec // path comes from detected source configuration
	if err == nil {
		return data, hostPath, nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return nil, hostPath, err
	}
	if runner == nil {
		return nil, hostPath, err
	}
	output, execErr := runner.Output(ctx, "podman", "exec", sourceContainerName, "cat", containerPath)
	// Record before writing: a write or cp that creates hostPath and then fails
	// must still be undone on rollback. hostPath was absent above, so this never
	// marks a pre-existing file for removal.
	if execErr == nil {
		recordPersisted(persisted, hostPath)
		if writeErr := os.WriteFile(hostPath, []byte(output), 0o600); writeErr != nil {
			slog.Warn("could not persist config material to host", "path", hostPath, "err", writeErr)
		} else {
			slog.Info("persisted config material from container to host", "path", hostPath)
		}
		return []byte(output), containerPath, nil
	}

	recordPersisted(persisted, hostPath)
	cpErr := podmanCpToHost(ctx, runner, sourceContainerName, containerPath, hostPath)
	if cpErr == nil {
		if chmodErr := os.Chmod(hostPath, 0o600); chmodErr != nil {
			return nil, hostPath, fmt.Errorf("restrict permissions on extracted file %s: %w", hostPath, chmodErr)
		}
		data, readErr := os.ReadFile(hostPath) //nolint:gosec // path from detected source configuration
		if readErr == nil {
			slog.Info("recovered config material via podman cp", "path", hostPath)
			return data, hostPath, nil
		}
		return nil, hostPath, fmt.Errorf("read extracted file %s: %w", hostPath, readErr)
	}

	return nil, containerPath, fmt.Errorf(
		"read %s from source container: %w",
		containerPath, errors.Join(
			fmt.Errorf("exec: %w", execErr),
			fmt.Errorf("cp: %w", cpErr),
		),
	)
}

func recordPersisted(persisted *[]string, path string) {
	if persisted != nil {
		*persisted = append(*persisted, path)
	}
}

// removePersistedConfigMaterial deletes the files this run persisted into the
// source config dir. Quay's config validator stops loading certificates at the
// first one it cannot read, so a root 0600 quay.pem left there makes the old
// OMR report ssl.cert as missing and exit on restart.
func (m *Migrator) removePersistedConfigMaterial() error {
	var errs []error
	for _, path := range m.persistedConfigFiles {
		if err := os.Remove(path); err != nil && !errors.Is(err, os.ErrNotExist) {
			errs = append(errs, fmt.Errorf("remove persisted config material: %w", err))
		}
	}
	m.persistedConfigFiles = nil
	return errors.Join(errs...)
}

func podmanCpToHost(ctx context.Context, runner system.CommandRunner, container, containerPath, hostPath string) error {
	src := container + ":" + containerPath
	return runner.Run(ctx, "podman", "cp", src, hostPath)
}

func sourceConfigPaths(configDir, configured, defaultName string) (hostPath, containerPath string) {
	if configured == "" {
		return filepath.Join(configDir, defaultName), filepath.Join(sourceContainerConf, defaultName)
	}
	cleaned := filepath.Clean(configured)
	for _, prefix := range []string{"/conf/stack/", sourceContainerConf + "/stack/"} {
		if relative, ok := strings.CutPrefix(cleaned, prefix); ok {
			return filepath.Join(configDir, relative), filepath.Join(sourceContainerConf, "stack", relative)
		}
	}
	if filepath.IsAbs(cleaned) {
		return cleaned, cleaned
	}
	return filepath.Join(configDir, cleaned), filepath.Join(sourceContainerConf, "stack", cleaned)
}
