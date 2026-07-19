package cmd

import (
	"context"
	"database/sql"
	"encoding/json"
	"flag"
	"log/slog"
	"net/http"
	"net/url"
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
	registryauth "github.com/quay/quay/internal/registry/auth"
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
	hostname := fs.String("hostname", "localhost", "public registry hostname, including a non-default port")
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
	credentialVerifier := auth.NewDatabaseVerifier(db, databaseVerifierConfig)
	superUsersFullAccess := featureEnabled(resolved.Config.FeatureSuperUsers) && featureEnabled(resolved.Config.FeatureSuperUsersFullAccess)
	anonymousAccess := resolved.Config.FeatureAnonymousAccess == nil || *resolved.Config.FeatureAnonymousAccess

	grantResolver, err := distribution.NewGrantResolver(db, distribution.GrantResolverConfig{
		LibraryNamespace: resolved.Config.LibraryNamespace, SuperUsers: resolved.Config.SuperUsers,
		SuperUsersFullAccess: superUsersFullAccess,
	})
	if err != nil {
		slog.Error("registry grant resolver setup error", "err", err)
		return 1
	}
	maxFresh := time.Duration(resolved.Config.RegistryJWTAuthMaxFreshS) * time.Second
	tokenLifetime := min(5*time.Minute, maxFresh)
	signer, verifier, err := registryauth.NewES256Pair(registryauth.ES256Config{
		Issuer: registryauth.Issuer, Audience: resolved.Config.ServerHostname,
		MaxFresh: maxFresh, ClockSkew: 5 * time.Second,
	})
	if err != nil {
		slog.Error("registry token key setup error", "err", err)
		return 1
	}
	realm := (&url.URL{
		Scheme: resolved.Config.PreferredURLScheme,
		Host:   resolved.Config.ServerHostname,
		Path:   "/v2/auth",
	}).String()
	accessController, err := registryauth.NewController(registryauth.ControllerConfig{
		Realm: realm, Service: resolved.Config.ServerHostname,
		LibraryNamespace: resolved.Config.LibraryNamespace, Verifier: verifier,
	})
	if err != nil {
		slog.Error("registry access controller setup error", "err", err)
		return 1
	}
	tokenHandler, err := registryauth.NewHandler(registryauth.HandlerConfig{
		Service: resolved.Config.ServerHostname, LibraryNamespace: resolved.Config.LibraryNamespace,
		AnonymousAccess: anonymousAccess, Lifetime: tokenLifetime, Signer: signer,
		Authenticate: func(ctx context.Context, username, secret string) (registryauth.Identity, bool) {
			result := credentialVerifier.Verify(ctx, auth.Credentials{Username: username, Secret: secret})
			if !result.Authenticated {
				return registryauth.Identity{}, false
			}
			principal := result.Principal
			return registryauth.Identity{Subject: principal.Username, Principal: &principal}, true
		},
		ResolveGrants: grantResolver.Resolve,
	})
	if err != nil {
		slog.Error("registry token handler setup error", "err", err)
		return 1
	}

	reg, err := distribution.NewRegistry(ctx, &distribution.Config{
		StoragePath: resolved.StoragePath, ListenAddr: addr, Store: store, BlobLocker: blobLocks,
		LibraryNamespace: resolved.Config.LibraryNamespace, AccessController: accessController,
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
		Authenticator: auth.NewBasicAuthenticator(credentialVerifier),
		Realm:         resolved.Config.ServerHostname,
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
		referrersHandler := registry.NewReferrersHandler(store, accessController, &registry.ReferrersConfig{
			LibraryNamespace: resolved.Config.LibraryNamespace,
			LibrarySupport:   resolved.Config.FeatureLibrarySupport == nil || *resolved.Config.FeatureLibrarySupport,
		})
		v2Handler = registry.WrapWithReferrers(referrersHandler, distHandler)
	}

	mux := http.NewServeMux()
	mux.Handle("/healthz", healthHandler(db))
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/api/", api)
	mux.Handle("/v2/auth", tokenHandler)
	mux.Handle("/", v2Handler)

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
