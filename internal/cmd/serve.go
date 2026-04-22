package cmd

import (
	"context"
	"crypto/tls"
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
	configPath := fs.String("config", "", "path to config.yaml (default: $QUAY_CONFIG or ./config.yaml)")
	addr := fs.String("addr", "", "listen address override (default from config or :8443)")
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 1
	}

	// Load config.
	cfg, err := config.Load(resolveConfigPath(*configPath))
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// Resolve storage path from config.
	storagePath, err := resolveStoragePath(cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// Open SQLite for auth queries.
	dbPath, err := loadDBPath(resolveConfigPath(*configPath))
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error opening database: %v\n", err)
		return 1
	}
	defer func() { _ = db.Close() }()

	// Build distribution config.
	listenAddr := ":8443"
	if *addr != "" {
		listenAddr = *addr
	}
	distCfg := buildDistConfig(storagePath, cfg, db, listenAddr)

	// Root context canceled on SIGINT/SIGTERM.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	app := handlers.NewApp(ctx, distCfg)

	srv := &http.Server{
		Addr:              listenAddr,
		Handler:           app,
		ReadHeaderTimeout: 10 * time.Second,
		BaseContext:       func(_ net.Listener) context.Context { return ctx },
	}

	// TLS setup.
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

	srv.TLSConfig = &tls.Config{MinVersion: tls.VersionTLS12}
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
// Only one storage location is supported (multi-location is a full Quay feature).
func resolveStoragePath(cfg *config.Config) (string, error) {
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
		return path, nil
	}

	return "", fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG has no entries")
}
