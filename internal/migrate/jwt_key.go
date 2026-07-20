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
		key, _, err = loadApprovedRegistryJWTSigningKey(ctx, targetDBPath, m.Source.ConfigDir, sourceCfg, m.Runner)
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

func loadApprovedRegistryJWTSigningKey(ctx context.Context, dbPath, configDir string, cfg *config.Config, runner system.CommandRunner) (*rsa.PrivateKey, string, error) {
	privateBytes, privateSource, err := readSourceConfigMaterial(
		ctx, configDir, cfg.InstanceServiceKeyLocation, legacyPrivateKeyName, runner,
	)
	if err != nil {
		return nil, "", fmt.Errorf("load source registry JWT private key: %w", err)
	}
	key, err := jwtauth.ParsePrivateKey(privateBytes)
	if err != nil {
		return nil, "", fmt.Errorf("parse source registry JWT private key from %s: %w", privateSource, err)
	}
	kidBytes, kidSource, err := readSourceConfigMaterial(
		ctx, configDir, cfg.InstanceServiceKeyKIDLocation, legacyKeyIDName, runner,
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

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		return nil, "", fmt.Errorf("open source database for registry JWT key validation: %w", err)
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
		return nil, "", fmt.Errorf("source registry JWT key %q is not approved and unexpired for service %q", kid, cfg.InstanceServiceKeyService)
	}
	if err != nil {
		return nil, "", fmt.Errorf("query approved source registry JWT key: %w", err)
	}
	var jwk jose.JSONWebKey
	if err := json.Unmarshal([]byte(rawJWK), &jwk); err != nil {
		return nil, "", fmt.Errorf("parse approved source registry JWT JWK: %w", err)
	}
	if jwk.KeyID != "" && jwk.KeyID != kid {
		return nil, "", fmt.Errorf("approved source registry JWT JWK has mismatched key ID %q", jwk.KeyID)
	}
	publicJWK := jwk.Public()
	if !jwtauth.PublicKeysEqual(&key.PublicKey, publicJWK.Key) {
		return nil, "", fmt.Errorf("source registry JWT private key does not match approved database JWK")
	}
	return key, kid, nil
}

func readSourceConfigMaterial(
	ctx context.Context,
	configDir, configured, defaultName string,
	runner system.CommandRunner,
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
	if execErr != nil {
		return nil, containerPath, fmt.Errorf("read %s from source container: %w", containerPath, execErr)
	}
	return []byte(output), containerPath, nil
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
