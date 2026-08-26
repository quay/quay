package dal

import (
	"context"
	"database/sql"
	"errors"

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
func (a *Authorizer) CanAdminRepository(ctx context.Context, principal *auth.Principal, repo *repository.Repository) (bool, error) {
	if repo == nil {
		return false, nil
	}
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

// CanPullRepository reports whether principal can pull repo contents.
func (a *Authorizer) CanPullRepository(ctx context.Context, principal *auth.Principal, repo *repository.Repository) (bool, error) {
	if repo == nil {
		return false, nil
	}
	if !repo.NamespaceEnabled {
		return false, nil
	}
	if repo.State == repository.StateMarkedForDeletion {
		return false, nil
	}
	if repo.Visibility == repository.VisibilityPublic {
		return true, nil
	}
	if principal.IsAnonymous() {
		return false, nil
	}
	if _, ok := a.superUsers[principal.Username]; ok {
		return true, nil
	}

	allowed, err := a.queries.UserCanPullRepository(ctx, daldb.UserCanPullRepositoryParams{
		RepositoryID: repo.ID,
		Username:     principal.Username,
		UserID:       sql.NullInt64{Int64: principal.ID, Valid: true},
	})
	if err != nil {
		return false, err
	}
	return allowed != 0, nil
}

// CanPushRepository reports whether principal can push repo contents.
func (a *Authorizer) CanPushRepository(ctx context.Context, principal *auth.Principal, repo *repository.Repository) (bool, error) {
	if repo == nil {
		return false, nil
	}
	if principal.IsAnonymous() {
		return false, nil
	}
	if !repo.NamespaceEnabled {
		return false, nil
	}
	if repo.KindID != repository.KindImage {
		return false, nil
	}
	switch repo.State {
	case repository.StateNormal:
	case repository.StateMirror:
		return a.canPushMirrorRepository(ctx, principal, repo.ID)
	case repository.StateOrgMirror:
		return a.canPushOrgMirrorRepository(ctx, principal, repo.ID)
	default:
		return false, nil
	}
	if _, ok := a.superUsers[principal.Username]; ok {
		return true, nil
	}

	allowed, err := a.queries.UserCanPushRepository(ctx, daldb.UserCanPushRepositoryParams{
		RepositoryID: repo.ID,
		Username:     principal.Username,
		UserID:       sql.NullInt64{Int64: principal.ID, Valid: true},
	})
	if err != nil {
		return false, err
	}
	return allowed != 0, nil
}

// CanCreateRepository reports whether principal can create repos in namespace.
func (a *Authorizer) CanCreateRepository(ctx context.Context, principal *auth.Principal, namespace string) (bool, error) {
	if principal.IsAnonymous() {
		return false, nil
	}
	_, isSuperUser := a.superUsers[principal.Username]
	namespaceUser, err := a.queries.GetNamespaceUserByUsername(ctx, namespace)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			if isSuperUser {
				return true, nil
			}
			return false, nil
		}
		return false, err
	}
	if !namespaceUser.Enabled {
		return false, nil
	}
	isOrgMirrored, err := a.queries.NamespaceIsOrgMirrored(ctx, namespace)
	if err != nil {
		return false, err
	}
	if isOrgMirrored != 0 {
		return false, nil
	}
	if isSuperUser {
		return true, nil
	}

	allowed, err := a.queries.UserCanCreateRepositoryInNamespace(ctx, daldb.UserCanCreateRepositoryInNamespaceParams{
		Namespace: namespace,
		Username:  principal.Username,
		UserID:    principal.ID,
	})
	if err != nil {
		return false, err
	}
	return allowed != 0, nil
}

func (a *Authorizer) canPushMirrorRepository(ctx context.Context, principal *auth.Principal, repositoryID int64) (bool, error) {
	if principal.Kind != auth.PrincipalRobot {
		return false, nil
	}
	allowed, err := a.queries.UserIsRepoMirrorRobot(ctx, daldb.UserIsRepoMirrorRobotParams{
		RepositoryID: repositoryID,
		UserID:       principal.ID,
	})
	if err != nil {
		return false, err
	}
	return allowed != 0, nil
}

func (a *Authorizer) canPushOrgMirrorRepository(ctx context.Context, principal *auth.Principal, repositoryID int64) (bool, error) {
	if principal.Kind != auth.PrincipalRobot {
		return false, nil
	}
	allowed, err := a.queries.UserIsOrgMirrorRobot(ctx, daldb.UserIsOrgMirrorRobotParams{
		RepositoryID: sql.NullInt64{Int64: repositoryID, Valid: true},
		UserID:       principal.ID,
	})
	if err != nil {
		return false, err
	}
	return allowed != 0, nil
}
