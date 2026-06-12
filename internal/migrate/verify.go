package migrate

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/quay/quay/internal/system"
)

// verify checks the live service is healthy after migration.
func (m *Migrator) verify(ctx context.Context) error {
	baseURL := fmt.Sprintf("https://%s:8443", m.Source.Hostname)

	client, err := m.tlsClient()
	if err != nil {
		return fmt.Errorf("create TLS client: %w", err)
	}

	slog.Info("verifying migrated registry", "url", baseURL)
	if err := system.WaitForHealth(ctx, client, baseURL+"/healthz", 30*time.Second); err != nil {
		return fmt.Errorf("health check: %w", err)
	}

	slog.Info("verification passed: registry is healthy")
	return nil
}

func (m *Migrator) tlsClient() (*http.Client, error) {
	certPath := filepath.Join(m.DataDir, "ssl.cert")
	certPEM, err := os.ReadFile(certPath) //nolint:gosec // path from data-dir
	if err != nil {
		return nil, fmt.Errorf("read cert: %w", err)
	}

	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(certPEM) {
		return nil, fmt.Errorf("parse cert PEM")
	}

	return &http.Client{
		Timeout: 5 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				MinVersion: tls.VersionTLS12,
				RootCAs:    pool,
			},
		},
	}, nil
}
