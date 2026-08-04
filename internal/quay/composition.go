package quay

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
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
)

type metricsConfig struct {
	registerer prometheus.Registerer
	gatherer   prometheus.Gatherer
}

type composition struct {
	handler   http.Handler
	db        *sql.DB
	reg       *distribution.Registry
	gcStore   gc.Store
	blobs     oci.BlobStore
	blobLocks oci.BlobLocker
}

func compose(ctx context.Context, cfg Config, resolved *config.Resolved, metricsCfg metricsConfig) (result composition, err error) {
	defer func() {
		if err != nil {
			if result.reg != nil {
				_ = result.reg.Close()
			}
			if result.db != nil {
				_ = result.db.Close()
			}
		}
	}()

	result.db, err = dbcore.Setup(ctx, resolved.DBPath)
	if err != nil {
		return result, fmt.Errorf("database setup: %w", err)
	}

	store, err := metastore.NewSQLiteStore(ctx, result.db)
	if err != nil {
		return result, fmt.Errorf("metastore setup: %w", err)
	}

	adminUsername, err := bootstrap.RequireAdminUser(ctx, result.db)
	if err != nil {
		return result, fmt.Errorf("registry is not initialized: %w", err)
	}
	configureStandaloneSuperuser(resolved, adminUsername)

	featureUserLastAccessed := cfg.Features.FeatureUserLastAccessed
	databaseVerifierConfig := auth.DatabaseVerifierConfig{
		DatabaseSecretKey:              resolved.Config.DatabaseSecretKey,
		RobotsDisallow:                 resolved.Config.RobotsDisallow,
		RobotsWhitelist:                resolved.Config.RobotsWhitelist,
		FeatureUserLastAccessed:        featureUserLastAccessed,
		LastAccessedUpdateThresholdSec: resolved.Config.LastAccessedUpdateThresholdS,
	}
	jwtService, tokenRealm, err := loadRegistryTokenService(resolved)
	if err != nil {
		return result, fmt.Errorf("registry token service: %w", err)
	}

	result.blobLocks = oci.NewBlobLockSet()
	result.reg, err = distribution.NewRegistry(ctx, &distribution.Config{
		StoragePath:                        resolved.StoragePath,
		Hostname:                           resolved.Config.ServerHostname,
		TokenRealm:                         tokenRealm,
		ListenAddr:                         cfg.ListenAddr,
		DB:                                 result.db,
		Store:                              store,
		BlobLocker:                         result.blobLocks,
		LibraryNamespace:                   resolved.Config.LibraryNamespace,
		AnonymousAccess:                    cfg.Features.FeatureAnonymousAccess,
		DatabaseSecretKey:                  resolved.Config.DatabaseSecretKey,
		RobotsDisallow:                     resolved.Config.RobotsDisallow,
		RobotsWhitelist:                    resolved.Config.RobotsWhitelist,
		FeatureUserLastAccessed:            featureUserLastAccessed,
		LastAccessedUpdateThresholdSeconds: resolved.Config.LastAccessedUpdateThresholdS,
		SuperUsers:                         resolved.Config.SuperUsers,
		SuperUsersFullAccess:               cfg.Features.HasFullSuperuserAccess(),
		JWTService:                         jwtService,
		MetricsRegisterer:                  metricsCfg.registerer,
	})
	if err != nil {
		return result, fmt.Errorf("registry setup: %w", err)
	}

	superUsersFullAccess := cfg.Features.HasFullSuperuserAccess()
	repositoryService, err := repository.NewService(
		repositorydal.NewStore(result.db),
		repositorydal.NewAuthorizer(result.db, repositorydal.AuthorizerConfig{
			SuperUsers:           resolved.Config.SuperUsers,
			SuperUsersFullAccess: superUsersFullAccess,
		}),
	)
	if err != nil {
		return result, fmt.Errorf("repository service setup: %w", err)
	}

	api, err := apiv1.New(apiv1.Config{
		Authenticator: auth.NewBasicAuthenticator(auth.NewDatabaseVerifier(result.db, databaseVerifierConfig)),
		Realm:         resolved.Config.ServerHostname,
	}, repositoryapi.NewModule(repositoryService))
	if err != nil {
		return result, fmt.Errorf("api setup: %w", err)
	}

	distHandler := registrymw.SubjectHeaderMiddleware(result.reg.Handler())
	v2Handler := distHandler
	if cfg.Features.FeatureReferrersAPI {
		referrersHandler, referrersErr := registry.NewReferrersHandler(store, &registry.ReferrersConfig{
			LibraryNamespace: resolved.Config.LibraryNamespace,
			LibrarySupport:   cfg.Features.FeatureLibrarySupport,
			Authenticator:    result.reg.Authenticator(),
		})
		if referrersErr != nil {
			return result, fmt.Errorf("referrers handler setup: %w", referrersErr)
		}
		v2Handler = registry.WrapWithReferrers(referrersHandler, distHandler)
	}

	metricsHandler := promhttp.InstrumentMetricHandler(
		metricsCfg.registerer,
		promhttp.HandlerFor(metricsCfg.gatherer, promhttp.HandlerOpts{}),
	)
	mux := http.NewServeMux()
	mux.Handle("/healthz", healthHandler(result.db))
	mux.Handle("/metrics", metricsHandler)
	mux.Handle("/api/", api)
	mux.Handle("/v2/auth", result.reg.TokenHandler())
	mux.Handle("/", v2Handler)
	result.handler = mux

	result.blobs, err = local.New(resolved.StoragePath)
	if err != nil {
		return result, fmt.Errorf("blob store setup: %w", err)
	}
	result.gcStore = gc.NewSQLiteStore(result.db)
	return result, nil
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
