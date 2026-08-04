package cmd

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"net/http"

	"github.com/prometheus/client_golang/prometheus"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/quay"
	"github.com/quay/quay/internal/server"
	"github.com/quay/quay/internal/system"
)

func newServeCmd() *Command {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (optional, overrides flags)")
	dataDir := fs.String("data-dir", ".", "root directory for DB, storage, certs")
	hostname := fs.String("hostname", "localhost:8443", "public registry hostname, including port when non-default")
	addr := fs.String("addr", ":8443", "listen address")

	return &Command{
		Name:     "serve",
		Synopsis: "Start the OCI container registry",
		Flags:    fs,
		Run: func(ctx context.Context, _ *Command, _ []string) int {
			return runServe(ctx, *configPath, *dataDir, *hostname, *addr)
		},
	}
}

func runServe(ctx context.Context, configPath, dataDir, hostname, addr string) int {
	resolved, err := config.Resolve(configPath, dataDir, hostname)
	if err != nil {
		slog.Error("config error", "err", err)
		return 1
	}

	app, err := quay.New(ctx, &quay.Config{
		Resolved:          resolved,
		Features:          resolved.Config.Features,
		ListenAddr:        addr,
		MetricsRegisterer: prometheus.DefaultRegisterer,
		MetricsGatherer:   prometheus.DefaultGatherer,
	})
	if err != nil {
		slog.Error("application setup error", "err", err)
		return 1
	}
	defer func() { _ = app.Close() }()

	srv, err := newRegistryServer(ctx, app.Handler(), resolved, addr)
	if err != nil {
		slog.Error("server build error", "err", err)
		return 1
	}

	slog.Info("registry listening",
		"scheme", srv.Scheme(),
		"addr", srv.Addr(),
		"storage", resolved.StoragePath,
		"db", resolved.DBPath,
	)

	return srv.ListenAndServe(ctx)
}

func configureStandaloneSuperuser(resolved *config.Resolved, username string) {
	if !resolved.FromFile {
		resolved.Config.SuperUsers = []string{username}
	}
}

func registryTLSHostname(publicHostname string) (string, error) {
	return system.HostnameWithoutPort(publicHostname)
}

func newRegistryServer(ctx context.Context, handler http.Handler, resolved *config.Resolved, addr string) (*server.Server, error) {
	tlsHostname, err := registryTLSHostname(resolved.Config.ServerHostname)
	if err != nil {
		return nil, fmt.Errorf("invalid registry hostname %q: %w", resolved.Config.ServerHostname, err)
	}
	return server.New(ctx, handler, &server.Config{
		ListenAddr:      addr,
		Hostname:        tlsHostname,
		PreferredScheme: resolved.Config.PreferredURLScheme,
		CertDir:         resolved.DataDir,
		SSLProtocols:    resolved.Config.SSLProtocols,
	})
}
