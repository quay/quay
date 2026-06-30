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
)

// Config holds the parameters needed to construct the distribution registry.
type Config struct {
	StoragePath      string
	Hostname         string
	ListenAddr       string
	DB               *sql.DB
	Store            oci.MetadataStore
	LibraryNamespace string
	AnonymousAccess  *bool
}

// Registry wraps the distribution registry handler.
type Registry struct {
	handler http.Handler
	db      *sql.DB
}

// NewRegistry creates the distribution registry with metadata middleware.
func NewRegistry(ctx context.Context, cfg *Config) (*Registry, error) {
	if cfg == nil {
		return nil, fmt.Errorf("nil Config")
	}
	if cfg.Store == nil {
		return nil, fmt.Errorf("nil metastore store")
	}
	if cfg.DB == nil {
		return nil, fmt.Errorf("nil database")
	}

	libraryNamespace := cfg.LibraryNamespace
	if libraryNamespace == "" {
		libraryNamespace = defaultLibraryNamespace
	}

	local.RegisterMetadataStore(cfg.Store)

	if err := registrymw.Register(cfg.Store, libraryNamespace); err != nil {
		return nil, fmt.Errorf("register middleware: %w", err)
	}

	distCfg := &configuration.Configuration{
		Catalog: configuration.Catalog{MaxEntries: 1000},
		Storage: configuration.Storage{
			"quay": configuration.Parameters{
				"rootdirectory": cfg.StoragePath,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
		Auth: configuration.Auth{
			"quaydb": configuration.Parameters{
				"realm":            cfg.Hostname,
				"db":               cfg.DB,
				"libraryNamespace": libraryNamespace,
				"anonymousAccess":  anonymousAccessEnabled(cfg.AnonymousAccess),
			},
		},
	}
	distCfg.Middleware = map[string][]configuration.Middleware{
		repositoryResourceType: {{Name: registrymw.Name()}},
	}

	distCfg.HTTP.Addr = cfg.ListenAddr
	return &Registry{
		handler: handlers.NewApp(ctx, distCfg),
		db:      cfg.DB,
	}, nil
}

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
