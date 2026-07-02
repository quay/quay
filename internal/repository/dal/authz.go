package dal

import (
	"context"
	"database/sql"

	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/repository"
)

// AuthorizerConfig configures repository permission checks.
type AuthorizerConfig struct {
	SuperUsers           []string
	SuperUsersFullAccess bool
}

// Authorizer checks repository permissions against Quay permission tables.
type Authorizer struct {
	queries    *daldb.Queries
	superUsers map[string]struct{}
}

var _ repository.Authorizer = (*Authorizer)(nil)

// NewAuthorizer returns a DB-backed repository authorizer.
func NewAuthorizer(db *sql.DB, cfg AuthorizerConfig) *Authorizer {
	superUsers := map[string]struct{}{}
	if cfg.SuperUsersFullAccess {
		superUsers = make(map[string]struct{}, len(cfg.SuperUsers))
		for _, username := range cfg.SuperUsers {
			if username == "" {
				continue
			}
			superUsers[username] = struct{}{}
		}
	}
	return &Authorizer{queries: daldb.New(db), superUsers: superUsers}
}

// CanAdminRepository reports whether principal can administer repo.
func (a *Authorizer) CanAdminRepository(ctx context.Context, principal *auth.Principal, repo repository.Repository) (bool, error) {
	if principal.IsAnonymous() {
		return false, nil
	}
	if _, ok := a.superUsers[principal.Username]; ok {
		return true, nil
	}

	allowed, err := a.queries.UserCanAdminRepository(ctx, daldb.UserCanAdminRepositoryParams{
		RepositoryID: repo.ID,
		Username:     principal.Username,
		UserID:       sql.NullInt64{Int64: principal.ID, Valid: true},
	})
	if err != nil {
		return false, err
	}
	return allowed != 0, nil
}
