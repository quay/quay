// Package e2etest provides test-only helpers for exercising the composed
// registry over HTTP.
package e2etest

import (
	"context"
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

	closeOnce sync.Once
	closeErr  error
}

// New provisions an isolated registry and starts it on a loopback ephemeral
// port. The listener is reserved before mirrorregistry.New so the token realm and
// audience use the actual server address.
func New(tb testing.TB) *Harness {
	tb.Helper()
	t := tb

	server := httptest.NewUnstartedServer(nil)
	h := &Harness{
		server: server,
	}
	// Ensure constructor failures release the reserved listener. A second
	// cleanup is registered below after TempDir so it runs before TempDir's
	// cleanup and closes the application before its files are removed.
	t.Cleanup(server.Close)

	dataDir := t.TempDir()
	t.Cleanup(func() {
		if err := h.close(); err != nil {
			t.Errorf("close E2E harness: %v", err)
		}
	})

	addr := server.Listener.Addr().String()
	storagePath := filepath.Join(dataDir, "storage")
	resolved := &config.Resolved{
		Config:      config.NewDefault(addr, storagePath),
		DataDir:     dataDir,
		StoragePath: storagePath,
		DBPath:      filepath.Join(dataDir, "quay.db"),
	}
	resolved.Config.PreferredURLScheme = "http"

	ctx := t.Context()

	db, err := dbcore.Setup(ctx, resolved.DBPath)
	if err != nil {
		t.Fatalf("set up E2E database: %v", err)
	}
	created, err := bootstrap.AdminUser(ctx, db, e2eUsername, e2ePassword)
	if err != nil {
		_ = db.Close()
		t.Fatalf("provision E2E administrator: %v", err)
	}
	if !created {
		_ = db.Close()
		t.Fatalf("provision E2E administrator: database was not empty")
	}
	if err := db.Close(); err != nil {
		t.Fatalf("close bootstrap database: %v", err)
	}

	app, err := mirrorregistry.New(ctx, &mirrorregistry.Config{
		Resolved:   resolved,
		Features:   resolved.Config.Features,
		ListenAddr: addr,
	})
	if err != nil {
		t.Fatalf("compose E2E application: %v", err)
	}
	h.app = app

	server.Config.Handler = app.Handler()
	server.Start()
	h.client = server.Client()
	h.client.Timeout = clientTimeout
	h.registry = newRegistryClient(server.URL, h.client, e2eUsername, e2ePassword)

	if err := h.checkHealth(ctx); err != nil {
		t.Fatalf("wait for E2E application health: %v", err)
	}
	return h
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
