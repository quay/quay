// Package quay composes the runnable Go Quay application.
package quay

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/http"
	"sync"

	"github.com/prometheus/client_golang/prometheus"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/registry/distribution"
)

// Config contains the resolved settings and runtime dependencies needed to
// compose an application. ListenAddr is passed to Distribution as handler
// configuration; it does not bind a socket.
type Config struct {
	Resolved          *config.Resolved
	Features          config.Features
	ListenAddr        string
	MetricsRegisterer prometheus.Registerer
	MetricsGatherer   prometheus.Gatherer
}

// App is one composed Go Quay HTTP application and its owned resources.
type App struct {
	handler http.Handler
	db      *sql.DB
	reg     *distribution.Registry

	cancel     context.CancelFunc
	workerDone chan struct{}

	closeOnce sync.Once
	closeErr  error
}

// New composes the production application handler and starts its background
// garbage collector.
func New(ctx context.Context, cfg *Config) (app *App, err error) {
	if ctx == nil {
		return nil, fmt.Errorf("nil context")
	}
	if cfg == nil {
		return nil, fmt.Errorf("nil application config")
	}

	metricsCfg, err := resolveMetrics(cfg)
	if err != nil {
		return nil, err
	}
	resolved, err := cloneResolved(cfg.Resolved)
	if err != nil {
		return nil, err
	}

	appCtx, cancel := context.WithCancel(ctx)
	defer func() {
		if err != nil {
			cancel()
		}
	}()

	composition, err := compose(appCtx, cfg, resolved, metricsCfg)
	if err != nil {
		return nil, err
	}

	app = &App{
		handler: composition.handler,
		db:      composition.db,
		reg:     composition.reg,
		cancel:  cancel,
	}
	app.workerDone = startGC(appCtx, composition.gcStore, composition.blobs, composition.blobLocks)
	return app, nil
}

// Handler returns the same top-level handler used by the production server.
func (a *App) Handler() http.Handler {
	if a == nil {
		return nil
	}
	return a.handler
}

// Close stops the garbage collector before releasing the registry and
// database. It is safe to call more than once and is nil-safe.
func (a *App) Close() error {
	if a == nil {
		return nil
	}
	a.closeOnce.Do(func() {
		if a.cancel != nil {
			a.cancel()
		}
		if a.workerDone != nil {
			<-a.workerDone
		}
		if a.reg != nil {
			a.closeErr = errors.Join(a.closeErr, a.reg.Close())
		}
		if a.db != nil {
			a.closeErr = errors.Join(a.closeErr, a.db.Close())
		}
	})
	return a.closeErr
}

func resolveMetrics(cfg *Config) (metricsConfig, error) {
	if cfg.MetricsRegisterer == nil && cfg.MetricsGatherer == nil {
		registry := prometheus.NewRegistry()
		return metricsConfig{registerer: registry, gatherer: registry}, nil
	}
	if cfg.MetricsRegisterer == nil || cfg.MetricsGatherer == nil {
		return metricsConfig{}, fmt.Errorf("metrics registerer and gatherer must be provided together")
	}
	return metricsConfig{registerer: cfg.MetricsRegisterer, gatherer: cfg.MetricsGatherer}, nil
}

func cloneResolved(resolved *config.Resolved) (*config.Resolved, error) {
	if resolved == nil {
		return nil, fmt.Errorf("nil resolved config")
	}
	if resolved.Config == nil {
		return nil, fmt.Errorf("nil resolved config.Config")
	}

	copyResolved := *resolved
	copyConfig := *resolved.Config
	copyConfig.SuperUsers = append([]string(nil), resolved.Config.SuperUsers...)
	copyConfig.RobotsWhitelist = append([]string(nil), resolved.Config.RobotsWhitelist...)
	copyResolved.Config = &copyConfig
	return &copyResolved, nil
}
