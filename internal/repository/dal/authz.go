// Package dal implements repository permission checks against Quay permission tables.
package dal

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/repository"
)

// libraryNamespace receives repositories pushed without a namespace under the
// default LIBRARY_NAMESPACE, so only a superuser may create it on push.
const libraryNamespace = "library"

// AuthorizerConfig configures repository permission checks.
type AuthorizerConfig struct {
	SuperUsers           []string
	SuperUsersFullAccess bool
}

// Authorizer checks repository permissions against Quay permission tables.
type Authorizer struct {
	db         *sql.DB
	queries    *daldb.Queries
	superUsers map[string]struct{}
}

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
	return &Authorizer{
		db:         db,
		queries:    daldb.New(db),
		superUsers: superUsers,
	}
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
	return allowed, nil
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
	return allowed, nil
}

// CanCreateRepository reports whether principal can create repos in namespace.
func (a *Authorizer) CanCreateRepository(ctx context.Context, principal *auth.Principal, namespace string) (bool, error) {
	return a.canCreateRepository(ctx, principal, namespace, false)
}

// CanCreateRepositoryOnPush is CanCreateRepository for a push. When principal
// is a user and namespace is missing, it creates the namespace as an
// organization whose owners team holds principal, so later pushes pass the
// regular permission checks.
func (a *Authorizer) CanCreateRepositoryOnPush(ctx context.Context, principal *auth.Principal, namespace string) (bool, error) {
	return a.canCreateRepository(ctx, principal, namespace, true)
}

func (a *Authorizer) canCreateRepository(ctx context.Context, principal *auth.Principal, namespace string, createNamespace bool) (bool, error) {
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
			// A pull token must not grant access to a namespace that another
			// user creates while the token is still valid.
			if !createNamespace {
				return false, nil
			}
			// The token endpoint passes the raw scope name; 2.x validated it
			// before creating the organization.
			if principal.Kind != auth.PrincipalUser || !auth.ValidUsername(namespace) {
				return false, nil
			}
			if namespace == libraryNamespace {
				return false, nil
			}
			if err := a.createOwnedNamespace(ctx, principal, namespace); err != nil {
				return false, err
			}
			// Re-check against the stored ACL: a concurrent push may have
			// claimed the namespace first.
			return a.canCreateRepository(ctx, principal, namespace, false)
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
	if isOrgMirrored {
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
	return allowed, nil
}

// createOwnedNamespace creates namespace as an organization whose owners team
// holds principal, as 2.x Quay did when creating a namespace on push. It is a
// no-op when the namespace already exists.
func (a *Authorizer) createOwnedNamespace(ctx context.Context, principal *auth.Principal, namespace string) error {
	tx, err := a.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := a.queries.WithTx(tx)

	orgID, err := q.CreateNamespaceOrganization(ctx, namespace)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("create namespace %q: %w", namespace, err)
	}
	teamID, err := q.CreateOwnersTeam(ctx, orgID)
	if err != nil {
		return fmt.Errorf("create owners team for %q: %w", namespace, err)
	}
	if err := q.AddTeamMember(ctx, daldb.AddTeamMemberParams{UserID: principal.ID, TeamID: teamID}); err != nil {
		return fmt.Errorf("add %q to owners of %q: %w", principal.Username, namespace, err)
	}
	return tx.Commit()
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
	return allowed, nil
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
	return allowed, nil
}
