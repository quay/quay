package cmd

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"

	// Registers the filesystem storage driver with the distribution driver factory.
	_ "github.com/distribution/distribution/v3/registry/storage/driver/filesystem"

	"github.com/quay/quay/internal/config"
)

func runServe(args []string) int {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to Quay config.yaml or config directory")
	addr := fs.String("addr", "127.0.0.1:5000", "listen address (host:port)")
	root := fs.String("root", "/var/lib/registry", "root directory for image storage")
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 1
	}

	// Track which flags were explicitly set so CLI overrides only apply
	// when the user actually provided them.
	explicit := make(map[string]bool)
	fs.Visit(func(f *flag.Flag) { explicit[f.Name] = true })

	cfg, err := buildConfig(*configPath, *addr, *root, explicit)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	listenAddr, storageRoot := resolveListenConfig(cfg, *root)

	// Root context canceled on SIGINT/SIGTERM; propagates to the
	// distribution app and all in-flight HTTP requests.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// NewApp wires up all OCI Distribution Spec endpoints (/v2/, manifests,
	// blobs, uploads, tags, catalog). The context enables cancellation.
	app := handlers.NewApp(ctx, cfg)

	srv := &http.Server{
		Addr:              listenAddr,
		Handler:           app,
		ReadHeaderTimeout: 10 * time.Second,

		// Derive request contexts from root so shutdown cancels in-flight requests.
		BaseContext: func(_ net.Listener) context.Context { return ctx },
	}

	errCh := make(chan error, 1)
	go func() {
		fmt.Fprintf(os.Stderr, "registry listening on %s (storage: %s)\n", listenAddr, storageRoot)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	select {
	case err := <-errCh:
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	case <-ctx.Done():
	}

	stop() // Restore default signal handling; second Ctrl-C kills immediately.

	fmt.Fprintln(os.Stderr, "\nshutting down...")

	// Fresh context for graceful drain; the root context is already canceled.
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		fmt.Fprintf(os.Stderr, "shutdown error: %v\n", err)
		return 1
	}

	fmt.Fprintln(os.Stderr, "stopped")
	return 0
}

// buildConfig constructs a distribution Configuration from a Quay config file
// (if provided) or falls back to a minimal hardcoded config. CLI flags in
// explicit override the corresponding config values.
func buildConfig(configPath, addr, root string, explicit map[string]bool) (*configuration.Configuration, error) {
	if configPath != "" {
		quayCfg, err := config.Load(configPath)
		if err != nil {
			return nil, err
		}

		cfg, err := config.ToDistribution(quayCfg)
		if err != nil {
			return nil, err
		}

		// CLI flags override config file values when explicitly set.
		if explicit["addr"] {
			cfg.HTTP.Addr = addr
		}
		if explicit["root"] {
			if fsCfg, ok := cfg.Storage["filesystem"]; ok {
				fsCfg["rootdirectory"] = root
				cfg.Storage["filesystem"] = fsCfg
			}
		}
		return cfg, nil
	}

	// No config file: minimal hardcoded config (original behavior).
	cfg := &configuration.Configuration{
		Storage: configuration.Storage{
			"filesystem": configuration.Parameters{
				"rootdirectory": root,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
	}
	cfg.HTTP.Addr = addr
	return cfg, nil
}

// resolveListenConfig extracts the listen address and storage root from a
// resolved configuration.
func resolveListenConfig(cfg *configuration.Configuration, rootDefault string) (listenAddr, storageRoot string) {
	listenAddr = cfg.HTTP.Addr
	storageRoot = rootDefault
	if fsCfg, ok := cfg.Storage["filesystem"]; ok {
		if dir, ok := fsCfg["rootdirectory"].(string); ok {
			storageRoot = dir
		}
	}
	return listenAddr, storageRoot
}
