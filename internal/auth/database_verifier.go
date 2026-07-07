package auth

import (
	"context"
	"database/sql"
)

// DatabaseVerifierConfig configures DB-backed credential verification.
type DatabaseVerifierConfig struct {
	DatabaseSecretKey              string
	RobotsDisallow                 bool
	RobotsWhitelist                []string
	FeatureUserLastAccessed        bool
	LastAccessedUpdateThresholdSec int
}

type databaseVerifier struct {
	user  Verifier
	robot Verifier
}

// NewDatabaseVerifier creates a DB-backed verifier for user and robot credentials.
func NewDatabaseVerifier(db *sql.DB, cfg DatabaseVerifierConfig) Verifier {
	return &databaseVerifier{
		user:  NewUserPasswordVerifier(db),
		robot: newRobotVerifier(db, cfg),
	}
}

func (v *databaseVerifier) Verify(ctx context.Context, creds Credentials) Result {
	if v == nil {
		return Result{Username: creds.Username, Presented: true}
	}

	if isRobotUsername(creds.Username) {
		if v.robot == nil {
			return Result{Username: creds.Username, Presented: true}
		}
		return v.robot.Verify(ctx, creds)
	}

	if v.user == nil {
		return Result{Username: creds.Username, Presented: true}
	}
	return v.user.Verify(ctx, creds)
}
