package cmd

import (
	"context"
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"

	apiv1 "github.com/quay/quay/internal/api/v1"
	repositoryapi "github.com/quay/quay/internal/api/v1/repository"
	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/bootstrap"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/gc"
	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage/local"
	"github.com/quay/quay/internal/registry"
	"github.com/quay/quay/internal/registry/distribution"
	registrymw "github.com/quay/quay/internal/registry/distribution/middleware"
	"github.com/quay/quay/internal/registry/jwtauth"
	"github.com/quay/quay/internal/repository"
	repositorydal "github.com/quay/quay/internal/repository/dal"
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
	blobLocks := oci.NewBlobLockSet()

	adminUsername, err := bootstrap.RequireAdminUser(ctx, db)
	if err != nil {
		slog.Error("registry is not initialized", "err", err)
		return 1
	}
	configureStandaloneSuperuser(resolved, adminUsername)

	featureUserLastAccessed := featureEnabled(resolved.Config.FeatureUserLastAccessed)
	lastAccessedUpdateThresholdSeconds := resolved.Config.LastAccessedUpdateThresholdS
	databaseVerifierConfig := auth.DatabaseVerifierConfig{
		DatabaseSecretKey:              resolved.Config.DatabaseSecretKey,
		RobotsDisallow:                 resolved.Config.RobotsDisallow,
		RobotsWhitelist:                resolved.Config.RobotsWhitelist,
		FeatureUserLastAccessed:        featureUserLastAccessed,
		LastAccessedUpdateThresholdSec: lastAccessedUpdateThresholdSeconds,
	}
	superUsersFullAccess := superUsersHaveFullAccess(resolved.Config)
	publicHostname := resolved.Config.ServerHostname
	tlsHostname, err := registryTLSHostname(publicHostname)
	if err != nil {
		slog.Error("invalid registry hostname", "hostname", publicHostname, "err", err)
		return 1
	}
	jwtService, tokenRealm, err := loadRegistryTokenService(resolved)
	if err != nil {
		slog.Error("registry token service error", "err", err)
		return 1
	}

	reg, err := distribution.NewRegistry(ctx, &distribution.Config{
		StoragePath:                        resolved.StoragePath,
		Hostname:                           publicHostname,
		TokenRealm:                         tokenRealm,
		ListenAddr:                         addr,
		DB:                                 db,
		Store:                              store,
		BlobLocker:                         blobLocks,
		LibraryNamespace:                   resolved.Config.LibraryNamespace,
		AnonymousAccess:                    resolved.Config.FeatureAnonymousAccess,
		DatabaseSecretKey:                  resolved.Config.DatabaseSecretKey,
		RobotsDisallow:                     resolved.Config.RobotsDisallow,
		RobotsWhitelist:                    resolved.Config.RobotsWhitelist,
		FeatureUserLastAccessed:            featureUserLastAccessed,
		LastAccessedUpdateThresholdSeconds: lastAccessedUpdateThresholdSeconds,
		SuperUsers:                         resolved.Config.SuperUsers,
		SuperUsersFullAccess:               superUsersFullAccess,
		JWTService:                         jwtService,
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
			SuperUsersFullAccess: superUsersFullAccess,
		}),
	)
	if err != nil {
		slog.Error("repository service setup error", "err", err)
		return 1
	}

	api, err := apiv1.New(apiv1.Config{
		Authenticator: auth.NewBasicAuthenticator(auth.NewDatabaseVerifier(db, databaseVerifierConfig)),
		Realm:         publicHostname,
	},
		repositoryapi.NewModule(repositoryService),
	)
	if err != nil {
		slog.Error("api setup error", "err", err)
		return 1
	}

	distHandler := registrymw.SubjectHeaderMiddleware(reg.Handler())

	referrersEnabled := resolved.Config.FeatureReferrersAPI == nil || *resolved.Config.FeatureReferrersAPI
	v2Handler := distHandler
	if referrersEnabled {
		referrersHandler, err := registry.NewReferrersHandler(store, &registry.ReferrersConfig{
			LibraryNamespace: resolved.Config.LibraryNamespace,
			LibrarySupport:   resolved.Config.FeatureLibrarySupport == nil || *resolved.Config.FeatureLibrarySupport,
			Authenticator:    reg.Authenticator(),
		})
		if err != nil {
			slog.Error("referrers handler setup error", "err", err)
			return 1
		}
		v2Handler = registry.WrapWithReferrers(referrersHandler, distHandler)
	}

	mux := http.NewServeMux()
	mux.Handle("/healthz", healthHandler(db))
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/api/", api)
	mux.Handle("/v2/auth", reg.TokenHandler())
	mux.Handle("/", v2Handler)

	srv, err := server.New(ctx, mux, &server.Config{
		ListenAddr:      addr,
		Hostname:        tlsHostname,
		PreferredScheme: resolved.Config.PreferredURLScheme,
		CertDir:         resolved.DataDir,
	})
	if err != nil {
		slog.Error("server build error", "err", err)
		return 1
	}

	blobs, err := local.New(resolved.StoragePath)
	if err != nil {
		slog.Error("blob store setup error", "err", err)
		return 1
	}
	gcStore := gc.NewSQLiteStore(db)
	collector := gc.NewCollector(gcStore, blobs, blobLocks, slog.Default())
	gcWorker := gc.NewWorker(collector, gc.DefaultConfig(), slog.Default())
	go func() { _ = gcWorker.Run(ctx) }()

	slog.Info("registry listening",
		"scheme", srv.Scheme(),
		"addr", srv.Addr(),
		"storage", resolved.StoragePath,
		"db", resolved.DBPath,
	)

	return srv.ListenAndServe(ctx)
}

func registryTLSHostname(publicHostname string) (string, error) {
	return system.HostnameWithoutPort(publicHostname)
}

func loadRegistryTokenService(resolved *config.Resolved) (*jwtauth.Service, string, error) {
	publicHostname := resolved.Config.ServerHostname
	service, err := jwtauth.LoadOrCreate(resolved.DataDir, jwtauth.Config{
		Issuer:   resolved.Config.InstanceServiceKeyService,
		Audience: publicHostname,
		MaxAge:   time.Duration(resolved.Config.RegistryJWTAuthMaxFreshS) * time.Second,
	})
	realm := fmt.Sprintf("%s://%s/v2/auth", resolved.Config.PreferredURLScheme, publicHostname)
	return service, realm, err
}

func superUsersHaveFullAccess(cfg *config.Config) bool {
	return featureEnabled(cfg.FeatureSuperUsers) && featureEnabled(cfg.FeatureSuperUsersFullAccess)
}

func configureStandaloneSuperuser(resolved *config.Resolved, username string) {
	if !resolved.FromFile {
		resolved.Config.SuperUsers = []string{username}
	}
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
