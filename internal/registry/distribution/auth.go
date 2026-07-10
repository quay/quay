package distribution

import (
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	distauth "github.com/distribution/distribution/v3/registry/auth"
	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
	repo "github.com/quay/quay/internal/repository"
	repositorydal "github.com/quay/quay/internal/repository/dal"
)

func init() {
	if err := distauth.Register("quaydb", distauth.InitFunc(newAccessController)); err != nil {
		slog.Error("failed to register quaydb auth", "err", err)
	}
}

type accessController struct {
	authenticator    *auth.BasicAuthenticator
	authorizer       *repositorydal.Authorizer
	queries          *daldb.Queries
	realm            string
	libraryNamespace string
	anonymousAccess  bool
}

var (
	_ distauth.AccessController = &accessController{}
	_ oci.Authenticator         = &accessController{}
)

const (
	repositoryPushAction   = "push"
	repositoryDeleteAction = "delete"
	registryResourceType   = "registry"
	registryCatalogName    = "catalog"
	registryCatalogAction  = "*"
	authOptionRealm        = "realm"
	authOptionAnonAccess   = "anonymousAccess"
)

func newAccessController(options map[string]interface{}) (distauth.AccessController, error) {
	realm, ok := options[authOptionRealm].(string)
	if !ok || realm == "" {
		return nil, fmt.Errorf("%q must be set for quaydb access controller", authOptionRealm)
	}

	db, ok := options["db"].(*sql.DB)
	if !ok || db == nil {
		return nil, fmt.Errorf(`"db" must be set to *sql.DB for quaydb access controller`)
	}

	libraryNamespace, _ := options["libraryNamespace"].(string)
	if libraryNamespace == "" {
		libraryNamespace = defaultLibraryNamespace
	}

	anonymousAccess, ok := options[authOptionAnonAccess].(bool)
	if !ok {
		anonymousAccess = true
	}

	databaseSecretKey, _ := options["databaseSecretKey"].(string)
	robotsDisallow, _ := options["robotsDisallow"].(bool)
	robotsWhitelist, _ := options["robotsWhitelist"].([]string)
	featureUserLastAccessed, _ := options["featureUserLastAccessed"].(bool)
	lastAccessedUpdateThresholdSeconds, _ := options["lastAccessedUpdateThresholdSeconds"].(int)
	superUsers, _ := options["superUsers"].([]string)
	superUsersFullAccess, _ := options["superUsersFullAccess"].(bool)

	verifier := auth.NewDatabaseVerifier(db, auth.DatabaseVerifierConfig{
		DatabaseSecretKey:              databaseSecretKey,
		RobotsDisallow:                 robotsDisallow,
		RobotsWhitelist:                robotsWhitelist,
		FeatureUserLastAccessed:        featureUserLastAccessed,
		LastAccessedUpdateThresholdSec: lastAccessedUpdateThresholdSeconds,
	})

	return &accessController{
		authenticator: auth.NewBasicAuthenticator(verifier),
		authorizer: repositorydal.NewAuthorizer(db, repositorydal.AuthorizerConfig{
			SuperUsers:           superUsers,
			SuperUsersFullAccess: superUsersFullAccess,
		}),
		queries:          daldb.New(db),
		realm:            realm,
		libraryNamespace: libraryNamespace,
		anonymousAccess:  anonymousAccess,
	}, nil
}

func (ac *accessController) Authorized(req *http.Request, access ...distauth.Access) (*distauth.Grant, error) {
	result := ac.authenticator.Authenticate(req)
	// Only missing credentials may fall back to anonymous public pulls. Invalid
	// credentials must fail instead of silently becoming anonymous.
	if !result.Authenticated && !result.Presented && ac.canAnonymousPull(req, access) {
		return &distauth.Grant{User: distauth.UserInfo{Name: auth.AnonymousPrincipal().Username}}, nil
	}

	if !result.Authenticated && !result.Presented {
		return nil, &challenge{
			realm: ac.realm,
			err:   distauth.ErrInvalidCredential,
		}
	}
	if !result.Authenticated {
		return nil, &challenge{
			realm: ac.realm,
			err:   distauth.ErrAuthenticationFailure,
		}
	}

	if err := ac.authorizeDistributionAccess(req, &result.Principal, access); err != nil {
		return nil, &challenge{
			realm: ac.realm,
			err:   distauth.ErrAuthenticationFailure,
		}
	}

	return &distauth.Grant{User: distauth.UserInfo{Name: result.Principal.Username}}, nil
}

func (ac *accessController) Authenticate(r *http.Request, access ...oci.Access) (*oci.Grant, error) {
	result := ac.authenticator.Authenticate(r)
	// Only missing credentials may fall back to anonymous public pulls. Invalid
	// credentials must fail instead of silently becoming anonymous.
	if !result.Authenticated && !result.Presented && ac.canAnonymousOCIPull(r, access) {
		return &oci.Grant{User: oci.User{Name: auth.AnonymousPrincipal().Username}}, nil
	}

	if !result.Authenticated {
		return nil, &challenge{
			realm: ac.realm,
			err:   oci.ErrUnauthorized,
		}
	}

	if err := ac.authorizeOCIAccess(r, &result.Principal, access); err != nil {
		return nil, &challenge{
			realm: ac.realm,
			err:   oci.ErrUnauthorized,
		}
	}

	return &oci.Grant{User: oci.User{Name: result.Principal.Username}}, nil
}

func (ac *accessController) canAnonymousPull(req *http.Request, access []distauth.Access) bool {
	if !ac.anonymousAccess || len(access) == 0 {
		return false
	}

	for _, item := range access {
		if item.Type != repositoryResourceType || item.Action != repositoryPullAction {
			return false
		}
		if !ac.repositoryIsPublic(req, item.Name) {
			return false
		}
	}
	return true
}

func (ac *accessController) canAnonymousOCIPull(req *http.Request, access []oci.Access) bool {
	if !ac.anonymousAccess || len(access) == 0 {
		return false
	}

	for _, item := range access {
		resourceType, resourceName, ok := strings.Cut(item.Resource, ":")
		if !ok || resourceType != repositoryResourceType || item.Action != repositoryPullAction {
			return false
		}
		if !ac.repositoryIsPublic(req, resourceName) {
			return false
		}
	}
	return true
}

func (ac *accessController) repositoryIsPublic(req *http.Request, name string) bool {
	namespace, repository, ok := ac.repositoryParts(name)
	if !ok {
		return false
	}

	isPublic, err := ac.queries.RepositoryIsPublicByNamespaceName(req.Context(), daldb.RepositoryIsPublicByNamespaceNameParams{
		Username: namespace,
		Name:     repository,
	})
	if err != nil {
		slog.Debug("anonymous repository visibility lookup failed", "repository", name, "err", err)
		return false
	}

	return isPublic
}

func (ac *accessController) authorizeDistributionAccess(req *http.Request, principal *auth.Principal, access []distauth.Access) error {
	if len(access) == 0 {
		return nil
	}

	for _, item := range access {
		switch item.Type {
		case repositoryResourceType:
			if err := ac.authorizeRepositoryAccess(req, principal, item, access); err != nil {
				return err
			}
		case registryResourceType:
			if item.Name == registryCatalogName && item.Action == registryCatalogAction {
				return fmt.Errorf("registry catalog is not supported by quaydb auth")
			}
			return fmt.Errorf("unsupported access resource type %q", item.Type)
		default:
			return fmt.Errorf("unsupported access resource type %q", item.Type)
		}
	}

	return nil
}

func (ac *accessController) authorizeOCIAccess(req *http.Request, principal *auth.Principal, access []oci.Access) error {
	if len(access) == 0 {
		return nil
	}

	distributionAccess := make([]distauth.Access, 0, len(access))
	for _, item := range access {
		resourceType, resourceName, ok := strings.Cut(item.Resource, ":")
		if !ok {
			return fmt.Errorf("invalid OCI access resource %q", item.Resource)
		}
		distributionAccess = append(distributionAccess, distauth.Access{
			Resource: distauth.Resource{
				Type: resourceType,
				Name: resourceName,
			},
			Action: item.Action,
		})
	}

	return ac.authorizeDistributionAccess(req, principal, distributionAccess)
}

func (ac *accessController) authorizeRepositoryAccess(req *http.Request, principal *auth.Principal, item distauth.Access, access []distauth.Access) error {
	repositoryRecord, err := ac.resolveRepository(req, item.Name)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return ac.authorizeMissingRepositoryAccess(req, principal, item, access)
		}
		return err
	}
	if repositoryRecord.KindID != repo.KindImage {
		return fmt.Errorf("repository %q is not an image repository", item.Name)
	}

	var allowed bool
	switch item.Action {
	case repositoryPullAction:
		allowed, err = ac.authorizer.CanPullRepository(req.Context(), principal, &repositoryRecord)
	case repositoryPushAction, repositoryDeleteAction:
		allowed, err = ac.authorizer.CanPushRepository(req.Context(), principal, &repositoryRecord)
	default:
		return fmt.Errorf("unsupported repository action %q", item.Action)
	}
	if err != nil {
		return err
	}
	if !allowed {
		return fmt.Errorf("repository action %q denied for %s", item.Action, principal.Username)
	}

	return nil
}

func (ac *accessController) authorizeMissingRepositoryAccess(req *http.Request, principal *auth.Principal, item distauth.Access, access []distauth.Access) error {
	switch item.Action {
	case repositoryPullAction:
		if accessIncludesRepositoryAction(access, item.Name, repositoryPushAction) {
			return nil
		}
		namespace, _, ok := ac.repositoryParts(item.Name)
		if !ok {
			return fmt.Errorf("invalid repository name %q", item.Name)
		}
		allowed, err := ac.authorizer.CanCreateRepository(req.Context(), principal, namespace)
		if err != nil {
			return err
		}
		if allowed {
			return nil
		}
		return sql.ErrNoRows
	case repositoryPushAction:
		namespace, _, ok := ac.repositoryParts(item.Name)
		if !ok {
			return fmt.Errorf("invalid repository name %q", item.Name)
		}
		allowed, err := ac.authorizer.CanCreateRepository(req.Context(), principal, namespace)
		if err != nil {
			return err
		}
		if !allowed {
			return fmt.Errorf("repository create denied for %s", principal.Username)
		}
		return nil
	case repositoryDeleteAction:
		return sql.ErrNoRows
	default:
		return fmt.Errorf("unsupported repository action %q", item.Action)
	}
}

func accessIncludesRepositoryAction(access []distauth.Access, name, action string) bool {
	for _, item := range access {
		if item.Type == repositoryResourceType && item.Name == name && item.Action == action {
			return true
		}
	}
	return false
}

func (ac *accessController) resolveRepository(req *http.Request, name string) (repo.Repository, error) {
	namespace, repository, ok := ac.repositoryParts(name)
	if !ok {
		return repo.Repository{}, fmt.Errorf("invalid repository name %q", name)
	}

	row, err := ac.queries.GetRepositoryAccessByNamespaceName(req.Context(), daldb.GetRepositoryAccessByNamespaceNameParams{
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

func (ac *accessController) repositoryParts(name string) (namespace, repository string, ok bool) {
	namespace, repository, ok = strings.Cut(name, "/")
	if !ok {
		namespace = ac.libraryNamespace
		repository = name
	}
	if namespace == "" || repository == "" {
		return "", "", false
	}
	return namespace, repository, true
}

// challenge implements auth.Challenge for Basic auth 401 responses.
type challenge struct {
	realm string
	err   error
}

var _ distauth.Challenge = challenge{}

func (ch challenge) SetHeaders(_ *http.Request, w http.ResponseWriter) {
	w.Header().Set("WWW-Authenticate", fmt.Sprintf("Basic realm=%q", ch.realm))
}

func (ch challenge) Error() string {
	return fmt.Sprintf("basic authentication challenge for realm %q: %s", ch.realm, ch.err)
}
