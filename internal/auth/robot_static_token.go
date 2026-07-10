package auth

import (
	"context"
	"crypto/subtle"
	"database/sql"
	"log/slog"
	"time"

	"github.com/quay/quay/internal/credentials/encryptedfield"
	"github.com/quay/quay/internal/dal/daldb"
)

// dummyEncryptedRobotValue keeps early robot auth failures on the decrypt/compare path.
const dummyEncryptedRobotValue = "v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==" // #nosec G101 -- encrypted dummy value, not a credential.

type robotVerifier struct {
	static *staticRobotTokenVerifier
}

func newRobotVerifier(db *sql.DB, cfg DatabaseVerifierConfig) Verifier {
	if db == nil {
		return nil
	}

	return &robotVerifier{static: newStaticRobotTokenVerifier(db, cfg)}
}

func (v *robotVerifier) Verify(ctx context.Context, creds Credentials) Result {
	if v == nil || v.static == nil {
		return failedRobotResult(creds.Username)
	}

	return v.static.Verify(ctx, creds)
}

type staticRobotTokenVerifier struct {
	queries                        *daldb.Queries
	databaseSecretKey              string
	robotsDisallow                 bool
	robotsWhitelist                map[string]struct{}
	featureUserLastAccessed        bool
	lastAccessedUpdateThresholdSec int
}

func newStaticRobotTokenVerifier(db *sql.DB, cfg DatabaseVerifierConfig) *staticRobotTokenVerifier {
	whitelist := make(map[string]struct{}, len(cfg.RobotsWhitelist))
	for _, username := range cfg.RobotsWhitelist {
		whitelist[username] = struct{}{}
	}

	return &staticRobotTokenVerifier{
		queries:                        daldb.New(db),
		databaseSecretKey:              cfg.DatabaseSecretKey,
		robotsDisallow:                 cfg.RobotsDisallow,
		robotsWhitelist:                whitelist,
		featureUserLastAccessed:        cfg.FeatureUserLastAccessed,
		lastAccessedUpdateThresholdSec: cfg.LastAccessedUpdateThresholdSec,
	}
}

func (v *staticRobotTokenVerifier) Verify(ctx context.Context, creds Credentials) Result {
	if v == nil || v.queries == nil {
		return failedRobotResult(creds.Username)
	}

	owner, ok := v.validateRequest(creds)
	if !ok {
		v.dummySecretMatch(creds)
		return failedRobotResult(creds.Username)
	}

	robot, ok := v.enabledRobot(ctx, creds.Username)
	if !ok {
		v.dummySecretMatch(creds)
		return failedRobotResult(creds.Username)
	}
	if !v.ownerEnabled(ctx, owner, creds.Username) {
		v.dummySecretMatch(creds)
		return failedRobotResult(creds.Username)
	}
	if !v.secretMatches(ctx, robot.ID, creds) {
		return failedRobotResult(creds.Username)
	}

	v.updateLastAccessed(ctx, robot.ID, robot.LastAccessed, creds.Username)

	return Result{
		Principal: Principal{
			ID:       robot.ID,
			UUID:     robot.Uuid,
			Username: robot.Username,
			Email:    robot.Email,
			Kind:     PrincipalRobot,
		},
		Username:      creds.Username,
		Presented:     true,
		Authenticated: true,
	}
}

func (v *staticRobotTokenVerifier) validateRequest(creds Credentials) (string, bool) {
	owner, _, ok := parseRobotUsername(creds.Username)
	if !ok {
		slog.Debug("robot authentication failed", "username", creds.Username, "reason", "invalid robot username")
		return "", false
	}
	if v.databaseSecretKey == "" {
		slog.Debug("robot authentication failed", "username", creds.Username, "reason", "missing database secret key")
		return "", false
	}
	if !isASCII(creds.Secret) {
		slog.Debug("robot authentication failed", "username", creds.Username, "reason", "non-ASCII secret")
		return "", false
	}
	if v.robotsDisallow {
		if _, ok := v.robotsWhitelist[creds.Username]; !ok {
			slog.Debug("robot authentication failed", "username", creds.Username, "reason", "robot disallowed")
			return "", false
		}
	}
	return owner, true
}

func (v *staticRobotTokenVerifier) enabledRobot(ctx context.Context, username string) (daldb.GetRobotByUsernameRow, bool) {
	robot, err := v.queries.GetRobotByUsername(ctx, username)
	if err != nil || !robot.Enabled {
		slog.Debug("robot authentication failed", "username", username, "reason", "robot missing or disabled")
		return daldb.GetRobotByUsernameRow{}, false
	}
	return robot, true
}

func (v *staticRobotTokenVerifier) ownerEnabled(ctx context.Context, owner, username string) bool {
	ownerUser, err := v.queries.GetNamespaceUserByUsername(ctx, owner)
	if err != nil || !ownerUser.Enabled {
		slog.Debug("robot authentication failed", "username", username, "reason", "owner missing or disabled")
		return false
	}
	return true
}

func (v *staticRobotTokenVerifier) secretMatches(ctx context.Context, robotID int64, creds Credentials) bool {
	encryptedToken, err := v.queries.GetRobotTokenByRobotID(ctx, robotID)
	if err != nil {
		slog.Debug("robot authentication failed", "username", creds.Username, "reason", "token row missing")
		return false
	}

	token, err := encryptedfield.Decrypt(v.databaseSecretKey, encryptedToken)
	if err != nil {
		slog.Debug("robot authentication failed", "username", creds.Username, "reason", "decrypt failed")
		return false
	}
	if subtle.ConstantTimeCompare([]byte(token), []byte(creds.Secret)) != 1 {
		slog.Debug("robot authentication failed", "username", creds.Username, "reason", "token mismatch")
		return false
	}
	return true
}

func (v *staticRobotTokenVerifier) dummySecretMatch(creds Credentials) {
	token, _ := encryptedfield.Decrypt(v.databaseSecretKey, dummyEncryptedRobotValue)
	subtle.ConstantTimeCompare([]byte(token), []byte(creds.Secret))
}

func (v *staticRobotTokenVerifier) updateLastAccessed(ctx context.Context, robotID int64, lastAccessed sql.NullTime, username string) {
	if !v.featureUserLastAccessed {
		return
	}
	if v.lastAccessedIsFresh(lastAccessed) {
		return
	}
	if err := v.queries.UpdateUserLastAccessedIfOlder(ctx, daldb.UpdateUserLastAccessedIfOlderParams{
		UserID:           robotID,
		ThresholdSeconds: int64(v.lastAccessedUpdateThresholdSec),
	}); err != nil {
		slog.Debug("robot last_accessed update failed", "username", username, "err", err)
	}
}

func (v *staticRobotTokenVerifier) lastAccessedIsFresh(lastAccessed sql.NullTime) bool {
	if !lastAccessed.Valid || v.lastAccessedUpdateThresholdSec <= 0 {
		return false
	}
	threshold := time.Duration(v.lastAccessedUpdateThresholdSec) * time.Second
	return time.Since(lastAccessed.Time) < threshold
}

func failedRobotResult(username string) Result {
	return Result{Username: username, Presented: true}
}
