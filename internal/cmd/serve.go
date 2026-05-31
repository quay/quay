package cmd

import (
	"context"
	"flag"
	"log/slog"
	"path/filepath"

	"github.com/quay/quay/internal/bootstrap"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/server"
)

func newServeCmd() *Command {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (optional, overrides flags)")
	dataDir := fs.String("data-dir", ".", "root directory for DB, storage, certs")
	hostname := fs.String("hostname", "localhost", "server hostname for TLS SANs")
	addr := fs.String("addr", ":8443", "listen address")
	adminUsername := fs.String("admin-username", "admin", "admin username (first run only)")

	return &Command{
		Name:     "serve",
		Synopsis: "Start the OCI container registry",
		Flags:    fs,
		Run: func(ctx context.Context, _ *Command, _ []string) int {
			return runServe(ctx, *configPath, *dataDir, *hostname, *addr, *adminUsername)
		},
	}
}

func runServe(ctx context.Context, configPath, dataDir, hostname, addr, adminUsername string) int {
	resolved, err := config.Resolve(configPath, dataDir, hostname)
	if err != nil {
		slog.Error("config error", "err", err)
		return 1
	}

	db, err := dbcore.OpenSQLite(resolved.DBPath)
	if err != nil {
		slog.Error("error opening database", "err", err)
		return 1
	}
	defer func() { _ = db.Close() }()

	if err := dbcore.Bootstrap(ctx, db, resolved.DBPath); err != nil {
		slog.Error("bootstrap database error", "err", err)
		return 1
	}

	authDir := filepath.Join(filepath.Dir(resolved.DBPath), "auth")
	if _, err := bootstrap.AdminUser(ctx, db, adminUsername, authDir); err != nil {
		slog.Error("bootstrap admin user error", "err", err)
		return 1
	}

	srv, err := server.New(ctx, &server.Config{
		ListenAddr:      addr,
		StoragePath:     resolved.StoragePath,
		Hostname:        resolved.Config.ServerHostname,
		PreferredScheme: resolved.Config.PreferredURLScheme,
		DBPath:          resolved.DBPath,
		DB:              db,
	})
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
