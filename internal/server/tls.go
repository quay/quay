package server

import (
	"fmt"
	"log/slog"
	"net/http"
	"path/filepath"

	"github.com/quay/quay/internal/registry"
)

const defaultHostname = "localhost"

func ensureTLS(hostname, dbPath string, srv *http.Server) (certPath, keyPath string, err error) {
	certDir := filepath.Dir(dbPath)
	certPath = filepath.Join(certDir, "ssl.cert")
	keyPath = filepath.Join(certDir, "ssl.key")

	if !registry.CertFilesExist(certPath, keyPath) {
		if hostname == "" {
			hostname = defaultHostname
		}
		slog.Info("generating self-signed certificate", "hostname", hostname)
		if err = registry.GenerateSelfSignedCert(hostname, certPath, keyPath); err != nil {
			return "", "", fmt.Errorf("generating certificate: %w", err)
		}
	}

	srv.TLSConfig = registry.SecureTLSConfig()
	return certPath, keyPath, nil
}
