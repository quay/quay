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
	"strings"
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

type serveOpts struct {
	configPath    string
	dataDir       string
	hostname      string
	addr          string
	adminUsername string
}

type resolvedConfig struct {
	cfg         *config.Config
	storagePath string
	dbPath      string
}

func runServe(args []string) int {
	opts, err := parseServeOpts(args)
	if err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 1
	}

	resolved, err := resolveServeConfig(opts)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	db, err := dbcore.OpenSQLite(resolved.dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error opening database: %v\n", err)
		return 1
	}
	defer func() { _ = db.Close() }()

	ctx := context.Background()
	if err := bootstrapDatabase(ctx, db, resolved.dbPath, os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	authDir := filepath.Join(filepath.Dir(resolved.dbPath), "auth")
	if _, err := bootstrapAdminUser(ctx, db, opts.adminUsername, authDir, os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	srv, useHTTPS, certPath, keyPath, err := buildServer(ctx, resolved, db, opts.addr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	scheme := "http"
	if useHTTPS {
		scheme = "https"
	}
	fmt.Fprintf(os.Stderr, "registry listening on %s://%s (storage: %s, db: %s)\n",
		scheme, opts.addr, resolved.storagePath, resolved.dbPath)

	return startAndWait(ctx, stop, srv, useHTTPS, certPath, keyPath)
}

// --- Flag parsing ---

func parseServeOpts(args []string) (serveOpts, error) {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (optional, overrides flags)")
	dataDir := fs.String("data-dir", ".", "root directory for DB, storage, certs")
	hostname := fs.String("hostname", "localhost", "server hostname for TLS SANs")
	addr := fs.String("addr", ":8443", "listen address")
	adminUsername := fs.String("admin-username", "admin", "admin username (first run only)")

	if err := fs.Parse(args); err != nil {
		return serveOpts{}, err
	}

	return serveOpts{
		configPath:    *configPath,
		dataDir:       *dataDir,
		hostname:      *hostname,
		addr:          *addr,
		adminUsername: *adminUsername,
	}, nil
}

// --- Config resolution ---

func resolveServeConfig(opts serveOpts) (*resolvedConfig, error) {
	if opts.configPath != "" {
		return resolveFromConfigFile(opts.configPath)
	}
	return resolveFromDefaults(opts.dataDir, opts.hostname)
}

func resolveFromConfigFile(configPath string) (*resolvedConfig, error) {
	resolved := resolveConfigPath(configPath)
	cfg, err := config.Load(resolved)
	if err != nil {
		return nil, err
	}
	storagePath, err := resolveStoragePath(cfg, resolved)
	if err != nil {
		return nil, err
	}
	dbPath, err := resolveDBPath(cfg, resolved)
	if err != nil {
		return nil, err
	}
	return &resolvedConfig{cfg: cfg, storagePath: storagePath, dbPath: dbPath}, nil
}

func resolveFromDefaults(dataDir, hostname string) (*resolvedConfig, error) {
	absDir, err := filepath.Abs(dataDir)
	if err != nil {
		return nil, fmt.Errorf("resolve data dir: %w", err)
	}
	storagePath := filepath.Join(absDir, "storage")

	for _, dir := range []string{absDir, storagePath} {
		if err := os.MkdirAll(dir, 0o750); err != nil {
			return nil, fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

	return &resolvedConfig{
		cfg:         buildDefaultConfig(hostname, storagePath),
		storagePath: storagePath,
		dbPath:      filepath.Join(absDir, "quay.db"),
	}, nil
}

func resolveConfigPath(flagValue string) string {
	if flagValue != "" {
		return flagValue
	}
	if env := os.Getenv("QUAY_CONFIG"); env != "" {
		return env
	}
	return "config.yaml"
}

func resolveDBPath(cfg *config.Config, configPath string) (string, error) {
	if cfg.DBURI == "" {
		return "", fmt.Errorf("DB_URI not set in config")
	}
	if !strings.HasPrefix(cfg.DBURI, "sqlite:///") {
		return "", fmt.Errorf("DB_URI must start with sqlite:/// for db commands (got %s)", cfg.DBURI)
	}
	dbPath := strings.TrimPrefix(cfg.DBURI, "sqlite:///")
	if !filepath.IsAbs(dbPath) {
		dbPath = filepath.Join(filepath.Dir(configPath), dbPath)
	}
	return dbPath, nil
}

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

// --- Server setup ---

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

func buildServer(ctx context.Context, resolved *resolvedConfig, db *sql.DB, listenAddr string) (srv *http.Server, useHTTPS bool, certPath, keyPath string, err error) {
	distCfg := buildDistConfig(resolved.storagePath, resolved.cfg, db, listenAddr)
	app := handlers.NewApp(ctx, distCfg)

	mux := http.NewServeMux()
	mux.Handle("/healthz", newHealthHandler(db))
	mux.Handle("/", app)

	srv = &http.Server{
		Addr:              listenAddr,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       120 * time.Second,
		BaseContext:       func(_ net.Listener) context.Context { return ctx },
	}

	useHTTPS = resolved.cfg.PreferredURLScheme == "https"
	if useHTTPS {
		certPath, keyPath, err = ensureServeTLS(resolved.cfg, resolved.dbPath, srv)
		if err != nil {
			return nil, false, "", "", err
		}
	}

	return srv, useHTTPS, certPath, keyPath, nil
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

func ensureServeTLS(cfg *config.Config, dbPath string, srv *http.Server) (certPath, keyPath string, err error) {
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

// --- Server lifecycle ---

func startAndWait(ctx context.Context, stop context.CancelFunc, srv *http.Server, useHTTPS bool, certPath, keyPath string) int {
	errCh := make(chan error, 1)
	go func() {
		if useHTTPS {
			errCh <- srv.ListenAndServeTLS(certPath, keyPath)
		} else {
			errCh <- srv.ListenAndServe()
		}
	}()

	select {
	case err := <-errCh:
		if !errors.Is(err, http.ErrServerClosed) {
			fmt.Fprintf(os.Stderr, "server error: %v\n", err)
			return 1
		}
		return 0
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
