package cmd

import (
	"context"
	"database/sql"
	"encoding/json"
	"flag"
	"log/slog"
	"net/http"
	"path/filepath"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"

	apiv1 "github.com/quay/quay/internal/api/v1"
	repositoryapi "github.com/quay/quay/internal/api/v1/repository"
	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/bootstrap"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/registry"
	"github.com/quay/quay/internal/registry/distribution"
	registrymw "github.com/quay/quay/internal/registry/distribution/middleware"
	"github.com/quay/quay/internal/repository"
	repositorydal "github.com/quay/quay/internal/repository/dal"
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

	db, err := dbcore.Setup(ctx, resolved.DBPath)
	if err != nil {
		slog.Error("database setup error", "err", err)
		return 1
	}
	defer func() { _ = db.Close() }()

	store, err := metastore.NewSQLiteStore(ctx, db)
	if err != nil {
		slog.Error("metastore setup error", "err", err)
		return 1
	}

	authDir := filepath.Join(resolved.DataDir, "auth")
	if _, err := bootstrap.AdminUser(ctx, db, adminUsername, authDir); err != nil {
		slog.Error("bootstrap admin user error", "err", err)
		return 1
	}

	reg, err := distribution.NewRegistry(ctx, &distribution.Config{
		StoragePath:      resolved.StoragePath,
		Hostname:         resolved.Config.ServerHostname,
		ListenAddr:       addr,
		DB:               db,
		Store:            store,
		LibraryNamespace: resolved.Config.LibraryNamespace,
		AnonymousAccess:  resolved.Config.FeatureAnonymousAccess,
	})
	if err != nil {
		slog.Error("registry setup error", "err", err)
		return 1
	}
	defer func() { _ = reg.Close() }()

	repositoryService, err := repository.NewService(
		repositorydal.NewStore(db),
		repositorydal.NewAuthorizer(db, repositorydal.AuthorizerConfig{
			SuperUsers:           resolved.Config.SuperUsers,
			SuperUsersFullAccess: featureEnabled(resolved.Config.FeatureSuperUsers) && featureEnabled(resolved.Config.FeatureSuperUsersFullAccess),
		}),
	)
	if err != nil {
		slog.Error("repository service setup error", "err", err)
		return 1
	}

	api, err := apiv1.New(apiv1.Config{
		Authenticator: auth.NewBasicAuthenticator(db),
		Realm:         resolved.Config.ServerHostname,
	},
		repositoryapi.NewModule(repositoryService),
	)
	if err != nil {
		slog.Error("api setup error", "err", err)
		return 1
	}

	referrersHandler := registry.NewReferrersHandler(db, store, registry.ReferrersConfig{
		LibraryNamespace: resolved.Config.LibraryNamespace,
		AnonymousAccess:  resolved.Config.FeatureAnonymousAccess == nil || *resolved.Config.FeatureAnonymousAccess,
	})

	mux := http.NewServeMux()
	mux.Handle("/healthz", healthHandler(db))
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/api/", api)
	mux.Handle("/", registry.WrapWithReferrers(referrersHandler, registrymw.SubjectHeaderMiddleware(reg.Handler())))

	srv, err := server.New(ctx, mux, &server.Config{
		ListenAddr:      addr,
		Hostname:        resolved.Config.ServerHostname,
		PreferredScheme: resolved.Config.PreferredURLScheme,
		CertDir:         resolved.DataDir,
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

func healthHandler(db *sql.DB) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()

		status := "ok"
		code := http.StatusOK
		var result int
		if err := db.QueryRowContext(ctx, "SELECT 1").Scan(&result); err != nil {
			status = "unhealthy"
			code = http.StatusServiceUnavailable
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(code)
		_ = json.NewEncoder(w).Encode(map[string]string{"status": status})
	})
}

func featureEnabled(configured *bool) bool {
	return configured != nil && *configured
}
