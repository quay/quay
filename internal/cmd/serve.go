package cmd

import (
	"context"
	"database/sql"
	"errors"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"

	// Registers the filesystem storage driver with the distribution driver factory.
	_ "github.com/distribution/distribution/v3/registry/storage/driver/filesystem"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/registry"
)

const defaultHostname = "localhost"

func runServe(args []string) int {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (optional, overrides flags)")
	dataDir := fs.String("data-dir", ".", "root directory for DB, storage, certs")
	hostname := fs.String("hostname", "localhost", "server hostname for TLS SANs")
	addr := fs.String("addr", ":8443", "listen address")
	adminUsername := fs.String("admin-username", "admin", "admin username (first run only)")
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 1
	}

	var cfg *config.Config
	var storagePath, dbPath string

	if *configPath != "" {
		var err error
		resolved := resolveConfigPath(*configPath)
		cfg, err = config.Load(resolved)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			return 1
		}
		storagePath, err = resolveStoragePath(cfg, resolved)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			return 1
		}
		dbPath, err = loadDBPath(resolved)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			return 1
		}
	} else {
		absDir, err := filepath.Abs(*dataDir)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error resolving data dir: %v\n", err)
			return 1
		}
		storagePath = filepath.Join(absDir, "storage")
		dbPath = filepath.Join(absDir, "quay.db")

		for _, dir := range []string{absDir, storagePath} {
			if err := os.MkdirAll(dir, 0o750); err != nil {
				fmt.Fprintf(os.Stderr, "error creating directory %s: %v\n", dir, err)
				return 1
			}
		}

		cfg = buildDefaultConfig(*hostname, storagePath)
	}

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error opening database: %v\n", err)
		return 1
	}
	defer func() { _ = db.Close() }()

	ctx := context.Background()
	if err := bootstrapDatabase(ctx, db, dbPath); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	authDir := filepath.Join(filepath.Dir(dbPath), "auth")
	if _, err := bootstrapAdminUser(ctx, db, *adminUsername, authDir); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	listenAddr := *addr
	distCfg := buildDistConfig(storagePath, cfg, db, listenAddr)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	app := handlers.NewApp(ctx, distCfg)

	mux := http.NewServeMux()
	mux.Handle("/healthz", newHealthHandler(db))
	mux.Handle("/", app)

	srv := &http.Server{
		Addr:              listenAddr,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       120 * time.Second,
		BaseContext:       func(_ net.Listener) context.Context { return ctx },
	}

	useHTTPS := cfg.PreferredURLScheme == "https"
	certPath, keyPath, err := ensureServeTLS(cfg, dbPath, useHTTPS, srv)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	return startAndWait(ctx, stop, srv, useHTTPS, certPath, keyPath, listenAddr, storagePath, dbPath)
}

func buildDistConfig(storagePath string, cfg *config.Config, db *sql.DB, listenAddr string) *configuration.Configuration {
	distCfg := &configuration.Configuration{
		Storage: configuration.Storage{
			"filesystem": configuration.Parameters{
				"rootdirectory": storagePath,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
		Auth: configuration.Auth{
			"quaydb": configuration.Parameters{
				"realm": cfg.ServerHostname,
				"db":    db,
			},
		},
	}
	distCfg.HTTP.Addr = listenAddr
	return distCfg
}

func buildDefaultConfig(hostname, storagePath string) *config.Config {
	return &config.Config{
		Server: config.Server{
			ServerHostname:     hostname,
			PreferredURLScheme: "https",
		},
		Storage: config.Storage{
			DistributedStorageConfig: config.StorageEntries{
				"default": {
					Driver: "LocalStorage",
					Params: map[string]any{"storage_path": storagePath},
				},
			},
			DefaultTagExpiration: "2w",
		},
	}
}

func ensureServeTLS(cfg *config.Config, dbPath string, useHTTPS bool, srv *http.Server) (certPath, keyPath string, err error) {
	if !useHTTPS {
		return "", "", nil
	}

	certDir := filepath.Dir(dbPath)
	certPath = filepath.Join(certDir, "ssl.cert")
	keyPath = filepath.Join(certDir, "ssl.key")

	if !registry.CertFilesExist(certPath, keyPath) {
		hostname := cfg.ServerHostname
		if hostname == "" {
			hostname = defaultHostname
		}
		fmt.Fprintf(os.Stderr, "generating self-signed certificate for %s\n", hostname)
		if err = registry.GenerateSelfSignedCert(hostname, certPath, keyPath); err != nil {
			return "", "", fmt.Errorf("generating certificate: %w", err)
		}
	}

	srv.TLSConfig = registry.SecureTLSConfig()
	return certPath, keyPath, nil
}

func startAndWait(ctx context.Context, stop context.CancelFunc, srv *http.Server, useHTTPS bool, certPath, keyPath, listenAddr, storagePath, dbPath string) int {
	errCh := make(chan error, 1)
	go func() {
		scheme := "http"
		if useHTTPS {
			scheme = "https"
		}
		fmt.Fprintf(os.Stderr, "registry listening on %s://%s (storage: %s, db: %s)\n",
			scheme, listenAddr, storagePath, dbPath)

		if useHTTPS {
			if err := srv.ListenAndServeTLS(certPath, keyPath); err != nil && !errors.Is(err, http.ErrServerClosed) {
				errCh <- err
			}
		} else {
			if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
				errCh <- err
			}
		}
	}()

	select {
	case err := <-errCh:
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	case <-ctx.Done():
	}

	stop()
	fmt.Fprintln(os.Stderr, "\nshutting down...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		fmt.Fprintf(os.Stderr, "shutdown error: %v\n", err)
		return 1
	}

	fmt.Fprintln(os.Stderr, "stopped")
	return 0
}

// resolveStoragePath extracts the filesystem storage path from config.
// Relative paths are resolved against the config file's directory.
// Only one storage location is supported (multi-location is a full Quay feature).
func resolveStoragePath(cfg *config.Config, configPath string) (string, error) {
	if len(cfg.DistributedStorageConfig) == 0 {
		return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG is not set")
	}
	if len(cfg.DistributedStorageConfig) > 1 {
		return "", fmt.Errorf("multiple storage locations not supported; use a single entry in DISTRIBUTED_STORAGE_CONFIG")
	}

	for id, entry := range cfg.DistributedStorageConfig {
		path, ok := entry.Params["storage_path"].(string)
		if !ok || path == "" {
			return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG.%s: missing storage_path", id)
		}
		if !filepath.IsAbs(path) {
			path = filepath.Join(filepath.Dir(configPath), path)
		}
		return path, nil
	}

	return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG has no entries")
}
