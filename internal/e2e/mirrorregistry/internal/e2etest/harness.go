// Package e2etest provides test-only helpers for exercising the composed
// registry over HTTP.
package e2etest

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"sync"
	"testing"

	"github.com/quay/quay/internal/bootstrap"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/gc"
	"github.com/quay/quay/internal/mirrorregistry"
)

const (
	e2eUsername = "admin"
	e2ePassword = "e2e-password"
)

// Harness owns one composed mirror-registry application and one in-process HTTP server.
// Every harness has an isolated database, storage directory, signing key, and
// listener.
type Harness struct {
	server   *httptest.Server
	app      *mirrorregistry.App
	client   *http.Client
	registry *RegistryClient
	gcDB     *sql.DB
	state    harnessState

	closeOnce sync.Once
	closeErr  error
}

type harnessState struct {
	dataDir     string
	storagePath string
	dbPath      string
}

// New provisions an isolated registry and starts it on a loopback ephemeral
// port. The listener is reserved before mirrorregistry.New so the token realm and
// audience use the actual server address.
func New(tb testing.TB) *Harness {
	tb.Helper()

	dataDir := tb.TempDir()
	state := harnessState{
		dataDir:     dataDir,
		storagePath: filepath.Join(dataDir, "storage"),
		dbPath:      filepath.Join(dataDir, "quay.db"),
	}

	db, err := dbcore.Setup(tb.Context(), state.dbPath)
	if err != nil {
		tb.Fatalf("set up E2E database: %v", err)
	}
	created, err := bootstrap.AdminUser(tb.Context(), db, e2eUsername, e2ePassword)
	if err != nil {
		_ = db.Close()
		tb.Fatalf("provision E2E administrator: %v", err)
	}
	if !created {
		_ = db.Close()
		tb.Fatalf("provision E2E administrator: database was not empty")
	}
	if err := db.Close(); err != nil {
		tb.Fatalf("close bootstrap database: %v", err)
	}

	return start(tb, state)
}

// Restart closes the current application and starts a new composition against
// the same database, storage, and signing material.
func (h *Harness) Restart(tb testing.TB) *Harness {
	tb.Helper()
	if h == nil {
		tb.Fatal("restart nil E2E harness")
		return nil
	}
	if err := h.close(); err != nil {
		tb.Fatalf("close E2E harness for restart: %v", err)
	}
	return start(tb, h.state)
}

func start(tb testing.TB, state harnessState) *Harness {
	tb.Helper()

	server := httptest.NewUnstartedServer(nil)
	h := &Harness{server: server, state: state}
	// Ensure constructor failures release the reserved listener. The harness
	// cleanup is registered afterward so it runs first and closes the
	// application before its temporary files are removed.
	tb.Cleanup(server.Close)
	tb.Cleanup(func() {
		if err := h.close(); err != nil {
			tb.Errorf("close E2E harness: %v", err)
		}
	})

	addr := server.Listener.Addr().String()
	resolved := &config.Resolved{
		Config:      config.NewDefault(addr, state.storagePath),
		DataDir:     state.dataDir,
		StoragePath: state.storagePath,
		DBPath:      state.dbPath,
	}
	resolved.Config.PreferredURLScheme = "http"

	app, err := mirrorregistry.New(tb.Context(), &mirrorregistry.Config{
		Resolved:   resolved,
		Features:   resolved.Config.Features,
		ListenAddr: addr,
	})
	if err != nil {
		tb.Fatalf("compose E2E application: %v", err)
	}
	h.app = app
	if app.GarbageCollector() == nil {
		tb.Fatal("compose E2E application without garbage collector")
	}

	h.gcDB, err = dbcore.Setup(tb.Context(), state.dbPath)
	if err != nil {
		tb.Fatalf("open E2E database for garbage collection fixtures: %v", err)
	}

	server.Config.Handler = app.Handler()
	server.Start()
	h.client = server.Client()
	h.client.Timeout = clientTimeout
	h.registry = newRegistryClient(server.URL, h.client, e2eUsername, e2ePassword)

	if err := h.checkHealth(tb.Context()); err != nil {
		tb.Fatalf("wait for E2E application health: %v", err)
	}
	return h
}

// CollectGarbage runs one synchronous production collector cycle. Tests must
// not issue registry writes concurrently with this call.
func (h *Harness) CollectGarbage(ctx context.Context) (gc.Stats, error) {
	if h == nil || h.app == nil || h.app.GarbageCollector() == nil {
		return gc.Stats{}, fmt.Errorf("collect garbage with uninitialized E2E harness")
	}
	return h.app.GarbageCollector().Collect(ctx)
}

// ExpireUploadProtection advances recently-uploaded blob fixture state past
// its one-hour retention window so a synchronous collector cycle can reclaim
// blobs that are no longer referenced by a manifest.
func (h *Harness) ExpireUploadProtection(ctx context.Context) error {
	if h == nil || h.gcDB == nil {
		return fmt.Errorf("expire uploads with uninitialized E2E harness")
	}
	_, err := h.gcDB.ExecContext(ctx, "UPDATE uploadedblob SET expires_at = datetime('now', '-1 second')")
	if err != nil {
		return fmt.Errorf("expire E2E uploaded blobs: %w", err)
	}
	return nil
}

// BaseURL returns the HTTP URL of the in-process registry.
func (h *Harness) BaseURL() string {
	if h == nil || h.server == nil {
		return ""
	}
	return h.server.URL
}

// HTTPClient returns the client connected to the in-process server.
func (h *Harness) HTTPClient() *http.Client {
	if h == nil {
		return nil
	}
	return h.client
}

// Registry returns the HTTP OCI registry client for this harness.
func (h *Harness) Registry() *RegistryClient {
	if h == nil {
		return nil
	}
	return h.registry
}

// close drains the HTTP server before closing the composed application. It is
// safe to call more than once and is nil-safe.
func (h *Harness) close() error {
	if h == nil {
		return nil
	}
	h.closeOnce.Do(func() {
		if h.server != nil {
			h.server.Close()
		}
		if h.client != nil {
			h.client.CloseIdleConnections()
		}
		if h.app != nil {
			h.closeErr = errors.Join(h.closeErr, h.app.Close())
		}
		if h.gcDB != nil {
			h.closeErr = errors.Join(h.closeErr, h.gcDB.Close())
		}
	})
	return h.closeErr
}

func (h *Harness) checkHealth(ctx context.Context) error {
	checkCtx, cancel := context.WithTimeout(ctx, healthTimeout)
	defer cancel()

	req, err := http.NewRequestWithContext(checkCtx, http.MethodGet, h.BaseURL()+"/healthz", http.NoBody)
	if err != nil {
		return err
	}
	resp, err := h.client.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()
	_, _ = io.Copy(io.Discard, resp.Body)
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check returned HTTP %d", resp.StatusCode)
	}
	return nil
}
