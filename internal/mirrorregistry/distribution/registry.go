// Package distribution assembles the mirror-registry integration with go-distribution.
package distribution

import (
	"context"
	"database/sql"
	"fmt"
	"io"
	"net/http"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"
	"github.com/prometheus/client_golang/prometheus"

	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage/local"
	sharedrt "github.com/quay/quay/internal/registry/distribution"
	registrymw "github.com/quay/quay/internal/registry/distribution/middleware"
	"github.com/quay/quay/internal/registry/jwtauth"
)

// Config holds the parameters needed to construct the mirror-registry
// distribution integration.
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

// Registry wraps the mirror-registry Distribution integration.
type Registry struct {
	runtime       *sharedrt.Runtime
	tokenHandler  *TokenHandler
	authenticator *BearerAuthenticator
}

// BearerAuthenticator adapts the concrete Distribution access controller to
// custom OCI endpoints.
type BearerAuthenticator struct{ controller *accessController }

// Authenticate validates a Bearer token for a custom OCI endpoint.
func (a *BearerAuthenticator) Authenticate(r *http.Request, access ...oci.Access) (*oci.Grant, error) {
	return a.controller.Authenticate(r, access...)
}

type appConstructor func(context.Context, *configuration.Configuration) *handlers.App
type afterAppConstructor func(*handlers.App)

func validateConfig(cfg *Config) error {
	if cfg == nil {
		return fmt.Errorf("nil Config")
	}
	if cfg.BlobLocker == nil {
		return fmt.Errorf("nil blob locker")
	}
	if cfg.Store == nil {
		return fmt.Errorf("nil metastore store")
	}
	if cfg.DB == nil {
		return fmt.Errorf("nil database")
	}
	if cfg.JWTService == nil {
		return fmt.Errorf("nil registry JWT service")
	}
	if cfg.Hostname == "" || cfg.TokenRealm == "" {
		return fmt.Errorf("registry token service and realm are required")
	}
	return nil
}

// NewRegistry creates the mirror-registry distribution integration with
// metadata middleware. Panics from Distribution's constructor are converted
// into errors by the shared runtime so callers can reliably clean up resources
// acquired before construction.
func NewRegistry(ctx context.Context, cfg *Config) (*Registry, error) {
	return newRegistry(ctx, cfg, handlers.NewApp, func(*handlers.App) {})
}

func newRegistry(ctx context.Context, cfg *Config, newApp appConstructor, afterApp afterAppConstructor) (*Registry, error) {
	if newApp == nil {
		return nil, fmt.Errorf("nil distribution app constructor")
	}
	if afterApp == nil {
		afterApp = func(*handlers.App) {}
	}

	var (
		tokenHandler  *TokenHandler
		authenticator *BearerAuthenticator
	)
	runtime, err := sharedrt.New(ctx, func(appCtx context.Context, onClose sharedrt.OnClose) (http.Handler, error) {
		if err := validateConfig(cfg); err != nil {
			return nil, err
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
			metrics, metricsErr := registrymw.NewMetrics(cfg.MetricsRegisterer)
			if metricsErr != nil {
				return nil, fmt.Errorf("create middleware metrics: %w", metricsErr)
			}
			onClose(func() error {
				metrics.Unregister()
				return nil
			})
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
		tokenHandler, err = newTokenHandler(
			controller.authenticator,
			controllerTokenPolicy{controller: controller},
			cfg.JWTService,
			controller.anonymousAccess,
		)
		if err != nil {
			return nil, err
		}
		authenticator = &BearerAuthenticator{controller: controller}

		storageParams := local.Parameters(cfg.StoragePath, cfg.Store)
		local.RegisterCloseRegistrar(storageParams, func(closer io.Closer) {
			onClose(func() error { return closer.Close() })
		})

		distCfg := &configuration.Configuration{
			Catalog: configuration.Catalog{MaxEntries: 1000},
			Storage: configuration.Storage{
				local.Name(): storageParams,
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
		distApp := newApp(appCtx, distCfg)
		onClose(distApp.Shutdown)
		afterApp(distApp)
		return distApp, nil
	})
	if err != nil {
		return nil, err
	}
	return &Registry{
		runtime:       runtime,
		tokenHandler:  tokenHandler,
		authenticator: authenticator,
	}, nil
}

// TokenHandler returns the Docker Registry token exchange endpoint.
func (a *Registry) TokenHandler() *TokenHandler { return a.tokenHandler }

// Authenticator returns the Bearer authenticator shared by custom OCI routes.
func (a *Registry) Authenticator() *BearerAuthenticator { return a.authenticator }

// Handler returns the HTTP handler for the registry.
func (a *Registry) Handler() http.Handler {
	if a == nil || a.runtime == nil {
		return nil
	}
	return a.runtime.Handler()
}

// Close releases resources held by the registry. It is idempotent and
// nil-safe.
func (a *Registry) Close() error {
	if a == nil || a.runtime == nil {
		return nil
	}
	return a.runtime.Close()
}
