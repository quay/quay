package distribution

import (
	"database/sql"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	distauth "github.com/distribution/distribution/v3/registry/auth"
	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
)

func init() {
	if err := distauth.Register("quaydb", distauth.InitFunc(newAccessController)); err != nil {
		slog.Error("failed to register quaydb auth", "err", err)
	}
}

type accessController struct {
	authenticator    *auth.BasicAuthenticator
	queries          *daldb.Queries
	realm            string
	libraryNamespace string
	anonymousAccess  bool
}

var (
	_ distauth.AccessController = &accessController{}
	_ oci.Authenticator         = &accessController{}
)

func newAccessController(options map[string]interface{}) (distauth.AccessController, error) {
	realm, ok := options["realm"].(string)
	if !ok || realm == "" {
		return nil, fmt.Errorf(`"realm" must be set for quaydb access controller`)
	}

	db, ok := options["db"].(*sql.DB)
	if !ok || db == nil {
		return nil, fmt.Errorf(`"db" must be set to *sql.DB for quaydb access controller`)
	}

	libraryNamespace, _ := options["libraryNamespace"].(string)
	if libraryNamespace == "" {
		libraryNamespace = defaultLibraryNamespace
	}

	anonymousAccess, ok := options["anonymousAccess"].(bool)
	if !ok {
		anonymousAccess = true
	}

	return &accessController{
		authenticator:    auth.NewBasicAuthenticator(db),
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

	return isPublic == 1
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
