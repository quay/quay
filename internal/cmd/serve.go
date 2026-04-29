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
	"github.com/distribution/distribution/v3/tracing"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"

	// Registers the filesystem storage driver with the distribution driver factory.
	_ "github.com/distribution/distribution/v3/registry/storage/driver/filesystem"
)

func runServe(args []string) int {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	addr := fs.String("addr", "127.0.0.1:5000", "listen address (host:port)")
	root := fs.String("root", "/var/lib/registry", "root directory for image storage")
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 1
	}

	// Minimal distribution config: filesystem storage with delete support.
	// Auth, TLS, and metrics are left unconfigured for local use.
	cfg := &configuration.Configuration{
		Storage: configuration.Storage{
			"filesystem": configuration.Parameters{
				"rootdirectory": *root,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
	}

	cfg.HTTP.Addr = *addr

	// Root context canceled on SIGINT/SIGTERM; propagates to the
	// distribution app and all in-flight HTTP requests.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// Initialize OpenTelemetry tracing. Uses the standard OTEL_* environment
	// variables for exporter configuration (e.g. OTEL_EXPORTER_OTLP_ENDPOINT).
	if err := tracing.InitOpenTelemetry(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "warning: failed to initialize tracing: %v\n", err)
	}

	// NewApp wires up all OCI Distribution Spec endpoints (/v2/, manifests,
	// blobs, uploads, tags, catalog). The context enables cancellation.
	app := handlers.NewApp(ctx, cfg)

	// Wrap with OpenTelemetry HTTP instrumentation to create per-request spans.
	handler := otelhttp.NewHandler(app, "",
		otelhttp.WithSpanNameFormatter(func(_ string, r *http.Request) string {
			return r.Method + " " + r.URL.Path
		}))

	srv := &http.Server{
		Addr:              *addr,
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,

		// Derive request contexts from root so shutdown cancels in-flight requests.
		BaseContext: func(_ net.Listener) context.Context { return ctx },
	}

	errCh := make(chan error, 1)
	go func() {
		fmt.Fprintf(os.Stderr, "registry listening on %s (storage: %s)\n", *addr, *root)
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

	// Flush any buffered trace spans.
	if tp, ok := otel.GetTracerProvider().(*sdktrace.TracerProvider); ok {
		if err := tp.Shutdown(shutdownCtx); err != nil {
			fmt.Fprintf(os.Stderr, "trace shutdown error: %v\n", err)
		}
	}

	fmt.Fprintln(os.Stderr, "stopped")
	return 0
}
