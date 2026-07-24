// Package distribution implements the OCI registry using go-distribution.
package distribution

import (
	"context"
	"database/sql"
	"fmt"
	"net/http"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"

	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage/local"
	registrymw "github.com/quay/quay/internal/registry/distribution/middleware"
	"github.com/quay/quay/internal/registry/jwtauth"
)

// Config holds the parameters needed to construct the distribution registry.
type Config struct {
	StoragePath                        string
	Hostname                           string
	TokenRealm                         string
	ListenAddr                         string
	DB                                 *sql.DB
	Store                              oci.MetadataStore
	BlobLocker                         oci.BlobLocker
	LibraryNamespace                   string
	AnonymousAccess                    *bool
	DatabaseSecretKey                  string
	RobotsDisallow                     bool
	RobotsWhitelist                    []string
	FeatureUserLastAccessed            bool
	LastAccessedUpdateThresholdSeconds int
	SuperUsers                         []string
	SuperUsersFullAccess               bool
	JWTService                         registryTokenService
}

type registryTokenService interface {
	tokenIssuer
	Authorize(string, []jwtauth.ResourceActions) (*jwtauth.Claims, error)
}

// Registry wraps the distribution registry handler.
type Registry struct {
	handler       http.Handler
	tokenHandler  *TokenHandler
	authenticator *BearerAuthenticator
	db            *sql.DB
}

// BearerAuthenticator adapts the concrete Distribution access controller to
// custom OCI endpoints.
type BearerAuthenticator struct{ controller *accessController }

// Authenticate validates a Bearer token for a custom OCI endpoint.
func (a *BearerAuthenticator) Authenticate(r *http.Request, access ...oci.Access) (*oci.Grant, error) {
	return a.controller.Authenticate(r, access...)
}

// NewRegistry creates the distribution registry with metadata middleware.
func NewRegistry(ctx context.Context, cfg *Config) (*Registry, error) {
	if cfg == nil {
		return nil, fmt.Errorf("nil Config")
	}
	if cfg.BlobLocker == nil {
		return nil, fmt.Errorf("nil blob locker")
	}
	if cfg.Store == nil {
		return nil, fmt.Errorf("nil metastore store")
	}
	if cfg.DB == nil {
		return nil, fmt.Errorf("nil database")
	}
	if cfg.JWTService == nil {
		return nil, fmt.Errorf("nil registry JWT service")
	}
	if cfg.Hostname == "" || cfg.TokenRealm == "" {
		return nil, fmt.Errorf("registry token service and realm are required")
	}

	libraryNamespace := cfg.LibraryNamespace
	if libraryNamespace == "" {
		libraryNamespace = defaultLibraryNamespace
	}

	local.Register()

	if err := registrymw.Register(cfg.Store, cfg.BlobLocker, libraryNamespace); err != nil {
		return nil, fmt.Errorf("register middleware: %w", err)
	}

	authOptions := configuration.Parameters{
		authOptionRealm:        cfg.TokenRealm,
		authOptionService:      cfg.Hostname,
		authOptionJWTService:   cfg.JWTService,
		"db":                   cfg.DB,
		"libraryNamespace":     libraryNamespace,
		authOptionAnonAccess:   anonymousAccessEnabled(cfg.AnonymousAccess),
		authOptionDatabaseKey:  cfg.DatabaseSecretKey,
		"robotsDisallow":       cfg.RobotsDisallow,
		"robotsWhitelist":      cfg.RobotsWhitelist,
		authOptionLastAccess:   cfg.FeatureUserLastAccessed,
		authOptionLastAccessS:  cfg.LastAccessedUpdateThresholdSeconds,
		"superUsers":           cfg.SuperUsers,
		"superUsersFullAccess": cfg.SuperUsersFullAccess,
	}
	controller, err := newAccessController(authOptions)
	if err != nil {
		return nil, fmt.Errorf("create registry access controller: %w", err)
	}
	tokenHandler, err := newTokenHandler(
		controller.authenticator,
		controllerTokenPolicy{controller: controller},
		cfg.JWTService,
		controller.anonymousAccess,
	)
	if err != nil {
		return nil, err
	}

	distCfg := &configuration.Configuration{
		Catalog: configuration.Catalog{MaxEntries: 1000},
		Storage: configuration.Storage{
			local.Name(): local.Parameters(cfg.StoragePath, cfg.Store),
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
		Auth: configuration.Auth{
			"quaydb": configuration.Parameters{
				authOptionController: controller,
			},
		},
	}
	distCfg.Middleware = map[string][]configuration.Middleware{
		repositoryResourceType: {{Name: registrymw.Name()}},
	}

	distCfg.HTTP.Addr = cfg.ListenAddr
	return &Registry{
		handler:       handlers.NewApp(ctx, distCfg),
		tokenHandler:  tokenHandler,
		authenticator: &BearerAuthenticator{controller: controller},
		db:            cfg.DB,
	}, nil
}

// TokenHandler returns the Docker Registry token exchange endpoint.
func (a *Registry) TokenHandler() *TokenHandler { return a.tokenHandler }

// Authenticator returns the Bearer authenticator shared by custom OCI routes.
func (a *Registry) Authenticator() *BearerAuthenticator { return a.authenticator }

// Handler returns the HTTP handler for the registry.
func (a *Registry) Handler() http.Handler {
	return a.handler
}

// Close releases resources held by the registry.
func (a *Registry) Close() error {
	return nil
}

func anonymousAccessEnabled(configured *bool) bool {
	if configured == nil {
		return true
	}
	return *configured
}
