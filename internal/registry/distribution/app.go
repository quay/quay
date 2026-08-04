// Package distribution implements the OCI registry using go-distribution.
package distribution

import (
	"context"
	"database/sql"
	"fmt"
	"net/http"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"
	"github.com/prometheus/client_golang/prometheus"

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
	AnonymousAccess                    bool
	DatabaseSecretKey                  string
	RobotsDisallow                     bool
	RobotsWhitelist                    []string
	FeatureUserLastAccessed            bool
	LastAccessedUpdateThresholdSeconds int
	SuperUsers                         []string
	SuperUsersFullAccess               bool
	JWTService                         registryTokenService
	// MetricsRegisterer is the Prometheus registerer for middleware metrics.
	// When nil, no metrics are recorded. Callers that want per-instance
	// metrics must provide an explicit registerer (e.g. prometheus.NewRegistry()).
	MetricsRegisterer prometheus.Registerer
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
	shutdown      func() error
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
// Panics from distribution's constructor are converted into errors so callers
// can reliably clean up resources acquired before construction.
func NewRegistry(ctx context.Context, cfg *Config) (registry *Registry, err error) {
	defer func() {
		if recovered := recover(); recovered != nil {
			registry = nil
			err = fmt.Errorf("distribution constructor panicked: %v", recovered)
		}
	}()

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

	if err := registrymw.Register(); err != nil {
		return nil, fmt.Errorf("register middleware: %w", err)
	}

	var metricsOpts []registrymw.Option
	if cfg.MetricsRegisterer != nil {
		metrics, err := registrymw.NewMetrics(cfg.MetricsRegisterer)
		if err != nil {
			return nil, fmt.Errorf("create middleware metrics: %w", err)
		}
		metricsOpts = append(metricsOpts, registrymw.WithMetrics(metrics))
	}

	authOptions := configuration.Parameters{
		authOptionRealm:        cfg.TokenRealm,
		authOptionService:      cfg.Hostname,
		authOptionJWTService:   cfg.JWTService,
		"db":                   cfg.DB,
		"libraryNamespace":     libraryNamespace,
		authOptionAnonAccess:   cfg.AnonymousAccess,
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
			"maintenance": configuration.Parameters{
				"uploadpurging": map[interface{}]interface{}{
					"enabled": false,
				},
			},
		},
		Auth: configuration.Auth{
			"quaydb": configuration.Parameters{
				authOptionController: controller,
			},
		},
	}
	distCfg.Middleware = map[string][]configuration.Middleware{
		repositoryResourceType: {{
			Name:    registrymw.Name(),
			Options: registrymw.Parameters(cfg.Store, cfg.BlobLocker, libraryNamespace, metricsOpts...),
		}},
	}

	distCfg.HTTP.Addr = cfg.ListenAddr
	distApp := handlers.NewApp(ctx, distCfg)
	return &Registry{
		handler:       distApp,
		tokenHandler:  tokenHandler,
		authenticator: &BearerAuthenticator{controller: controller},
		shutdown:      distApp.Shutdown,
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
	if a == nil || a.shutdown == nil {
		return nil
	}
	return a.shutdown()
}
