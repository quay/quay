package registry

import (
	"context"
	"database/sql"
	"net/http"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"

	// Registers the filesystem storage driver with the distribution driver factory.
	_ "github.com/distribution/distribution/v3/registry/storage/driver/filesystem"
)

// AppConfig holds the parameters needed to construct the distribution app.
type AppConfig struct {
	StoragePath string
	Hostname    string
	ListenAddr  string
	DB          *sql.DB
}

// NewApp returns the distribution registry handler configured with the given
// storage, auth, and catalog settings.
func NewApp(ctx context.Context, cfg AppConfig) http.Handler {
	distCfg := &configuration.Configuration{
		Catalog: configuration.Catalog{MaxEntries: 1000},
		Storage: configuration.Storage{
			"filesystem": configuration.Parameters{
				"rootdirectory": cfg.StoragePath,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
		Auth: configuration.Auth{
			"quaydb": configuration.Parameters{
				"realm": cfg.Hostname,
				"db":    cfg.DB,
			},
		},
	}
	distCfg.HTTP.Addr = cfg.ListenAddr
	return handlers.NewApp(ctx, distCfg)
}
