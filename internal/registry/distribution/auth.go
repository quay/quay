package distribution

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"slices"
	"sort"
	"strings"

	quayauth "github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	registryauth "github.com/quay/quay/internal/registry/auth"
	repo "github.com/quay/quay/internal/repository"
	repositorydal "github.com/quay/quay/internal/repository/dal"
)

const (
	repositoryPushAction   = "push"
	repositoryDeleteAction = "delete"
	repositoryAdminAction  = "*"
)

// GrantResolverConfig configures Quay repository authorization for registry
// token issuance.
type GrantResolverConfig struct {
	LibraryNamespace     string
	SuperUsers           []string
	SuperUsersFullAccess bool
}

// GrantResolver maps Quay repository RBAC to downscoped registry token grants.
// It performs no credential or JWT work.
type GrantResolver struct {
	authorizer       *repositorydal.Authorizer
	queries          *daldb.Queries
	libraryNamespace string
}

// NewGrantResolver constructs a DB-backed registry grant resolver.
func NewGrantResolver(db *sql.DB, cfg GrantResolverConfig) (*GrantResolver, error) {
	if db == nil {
		return nil, fmt.Errorf("nil database")
	}
	libraryNamespace := cfg.LibraryNamespace
	if libraryNamespace == "" {
		libraryNamespace = defaultLibraryNamespace
	}
	return &GrantResolver{
		authorizer: repositorydal.NewAuthorizer(db, repositorydal.AuthorizerConfig{
			SuperUsers: cfg.SuperUsers, SuperUsersFullAccess: cfg.SuperUsersFullAccess,
		}),
		queries:          daldb.New(db),
		libraryNamespace: libraryNamespace,
	}, nil
}

// Resolve returns the requested/allowed action intersection. Permission denial
// produces an empty action list; only lookup failures are returned as errors.
func (r *GrantResolver) Resolve(ctx context.Context, identity registryauth.Identity, scopes []registryauth.Scope) ([]registryauth.ResourceActions, error) {
	principal, err := r.principal(identity)
	if err != nil {
		return nil, err
	}

	grants := make([]registryauth.ResourceActions, 0, len(scopes))
	for _, scope := range scopes {
		grant := registryauth.ResourceActions{Type: scope.Type, Name: scope.Name, Actions: []string{}}
		if scope.Type == repositoryResourceType {
			grant.Actions, err = r.resolveRepositoryActions(ctx, principal, scope)
			if err != nil {
				return nil, err
			}
		}
		grants = append(grants, grant)
	}
	return grants, nil
}

func (r *GrantResolver) principal(identity registryauth.Identity) (*quayauth.Principal, error) {
	if identity.Anonymous {
		return quayauth.AnonymousPrincipal(), nil
	}
	principal, ok := identity.Principal.(*quayauth.Principal)
	if !ok || principal == nil || principal.IsAnonymous() || principal.Username != identity.Subject {
		return nil, fmt.Errorf("invalid authenticated principal")
	}
	return principal, nil
}

func (r *GrantResolver) resolveRepositoryActions(ctx context.Context, principal *quayauth.Principal, scope registryauth.Scope) ([]string, error) {
	repositoryRecord, err := r.resolveRepository(ctx, scope.Name)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			exists, existsErr := r.repositoryExists(ctx, scope.Name)
			if existsErr != nil {
				return nil, existsErr
			}
			if exists {
				return []string{}, nil
			}
			return r.resolveMissingRepositoryActions(ctx, principal, scope)
		}
		return nil, err
	}
	if repositoryRecord.KindID != repo.KindImage {
		return []string{}, nil
	}

	allowedActions := make([]string, 0, len(scope.Actions))
	for _, action := range scope.Actions {
		var allowed bool
		switch action {
		case repositoryPullAction:
			allowed, err = r.authorizer.CanPullRepository(ctx, principal, &repositoryRecord)
		case repositoryPushAction, repositoryDeleteAction:
			allowed, err = r.authorizer.CanPushRepository(ctx, principal, &repositoryRecord)
		case repositoryAdminAction:
			if repositoryRecord.State != repo.StateNormal || !repositoryRecord.NamespaceEnabled {
				continue
			}
			allowed, err = r.authorizer.CanAdminRepository(ctx, principal, &repositoryRecord)
		default:
			return nil, fmt.Errorf("unsupported repository action %q", action)
		}
		if err != nil {
			return nil, err
		}
		if allowed {
			allowedActions = append(allowedActions, action)
		}
	}
	sort.Strings(allowedActions)
	return allowedActions, nil
}

func (r *GrantResolver) repositoryExists(ctx context.Context, name string) (bool, error) {
	namespace, repository, ok := r.repositoryParts(name)
	if !ok {
		return false, fmt.Errorf("invalid repository name %q", name)
	}
	_, err := r.queries.GetRepositoryByNamespaceName(ctx, daldb.GetRepositoryByNamespaceNameParams{
		Username: namespace,
		Name:     repository,
	})
	if err == nil {
		return true, nil
	}
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	return false, err
}

func (r *GrantResolver) resolveMissingRepositoryActions(ctx context.Context, principal *quayauth.Principal, scope registryauth.Scope) ([]string, error) {
	namespace, _, ok := r.repositoryParts(scope.Name)
	if !ok {
		return nil, fmt.Errorf("invalid repository name %q", scope.Name)
	}
	requestedPull := slices.Contains(scope.Actions, repositoryPullAction)
	requestedPush := slices.Contains(scope.Actions, repositoryPushAction)
	if !requestedPull && !requestedPush {
		return []string{}, nil
	}
	canCreate, err := r.authorizer.CanCreateRepository(ctx, principal, namespace)
	if err != nil {
		return nil, err
	}
	if !canCreate {
		return []string{}, nil
	}

	allowedActions := make([]string, 0, 2)
	for _, action := range scope.Actions {
		if action == repositoryPullAction || action == repositoryPushAction {
			allowedActions = append(allowedActions, action)
		}
	}
	sort.Strings(allowedActions)
	return allowedActions, nil
}

func (r *GrantResolver) resolveRepository(ctx context.Context, name string) (repo.Repository, error) {
	namespace, repository, ok := r.repositoryParts(name)
	if !ok {
		return repo.Repository{}, fmt.Errorf("invalid repository name %q", name)
	}

	row, err := r.queries.GetRepositoryAccessByNamespaceName(ctx, daldb.GetRepositoryAccessByNamespaceNameParams{
		Username: namespace,
		Name:     repository,
	})
	if err != nil {
		return repo.Repository{}, err
	}

	return repo.Repository{
		ID: row.ID,
		Ref: repo.Ref{
			Namespace: row.Namespace,
			Name:      row.Name,
		},
		Visibility:       repo.Visibility(row.Visibility),
		State:            row.State,
		KindID:           row.KindID,
		NamespaceEnabled: row.NamespaceEnabled,
	}, nil
}

func (r *GrantResolver) repositoryParts(name string) (namespace, repository string, ok bool) {
	namespace, repository, ok = strings.Cut(name, "/")
	if !ok {
		namespace = r.libraryNamespace
		repository = name
	}
	if namespace == "" || repository == "" {
		return "", "", false
	}
	return namespace, repository, true
}
