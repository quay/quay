// Package server provides HTTP server construction and lifecycle management
// for the OCI container registry.
package server

import (
	"context"
	"database/sql"
	"errors"
	"log/slog"
	"net"
	"net/http"
	"time"

	"github.com/quay/quay/internal/registry"
)

const (
	schemeHTTPS = "https"

	readHeaderTimeout = 10 * time.Second
	idleTimeout       = 120 * time.Second
	shutdownTimeout   = 10 * time.Second
)

// Config holds the parameters needed to build a registry server.
type Config struct {
	ListenAddr      string
	StoragePath     string
	Hostname        string
	PreferredScheme string
	DBPath          string
	DB              *sql.DB
}

// Server wraps an *http.Server with registry-specific lifecycle.
type Server struct {
	srv      *http.Server
	useHTTPS bool
	certPath string
	keyPath  string
}

// New creates a Server with the distribution app, healthz endpoint, and
// optional TLS.
func New(ctx context.Context, cfg *Config, opts ...Option) (*Server, error) {
	var o options
	for _, fn := range opts {
		fn(&o)
	}

	app := registry.NewApp(ctx, registry.AppConfig{
		StoragePath: cfg.StoragePath,
		Hostname:    cfg.Hostname,
		ListenAddr:  cfg.ListenAddr,
		DB:          cfg.DB,
	})

	mux := http.NewServeMux()
	mux.Handle("/healthz", registry.NewHealthHandler(cfg.DB))
	for _, r := range o.extraRoutes {
		mux.Handle(r.pattern, r.handler)
	}
	mux.Handle("/", app)

	var handler http.Handler = mux
	if o.middleware != nil {
		handler = o.middleware(handler)
	}

	srv := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           handler,
		ReadHeaderTimeout: readHeaderTimeout,
		IdleTimeout:       idleTimeout,
		BaseContext:       func(_ net.Listener) context.Context { return ctx },
	}

	s := &Server{srv: srv}

	if cfg.PreferredScheme == schemeHTTPS {
		certPath, keyPath, err := ensureTLS(cfg.Hostname, cfg.DBPath, srv)
		if err != nil {
			return nil, err
		}
		s.useHTTPS = true
		s.certPath = certPath
		s.keyPath = keyPath
	}

	return s, nil
}

// ListenAndServe starts the server and blocks until the context is canceled
// or the server encounters a fatal error. It handles graceful shutdown.
func (s *Server) ListenAndServe(ctx context.Context) int {
	errCh := make(chan error, 1)
	go func() {
		if s.useHTTPS {
			errCh <- s.srv.ListenAndServeTLS(s.certPath, s.keyPath)
		} else {
			errCh <- s.srv.ListenAndServe()
		}
	}()

	select {
	case err := <-errCh:
		if !errors.Is(err, http.ErrServerClosed) {
			slog.Error("server error", "err", err)
			return 1
		}
		return 0
	case <-ctx.Done():
	}

	slog.Info("shutting down")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()

	if err := s.srv.Shutdown(shutdownCtx); err != nil {
		slog.Error("shutdown error", "err", err)
		return 1
	}

	slog.Info("stopped")
	return 0
}

// Addr returns the configured listen address.
func (s *Server) Addr() string {
	return s.srv.Addr
}

// Scheme returns "https" if TLS is enabled, "http" otherwise.
func (s *Server) Scheme() string {
	if s.useHTTPS {
		return schemeHTTPS
	}
	return "http"
}
