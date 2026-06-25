package server

import (
	"fmt"
	"log/slog"
	"net/http"
	"path/filepath"

	"github.com/quay/quay/internal/certs"
)

const defaultHostname = "localhost"

func ensureTLS(hostname, certDir string, srv *http.Server) (certPath, keyPath string, err error) {
	certPath = filepath.Join(certDir, "ssl.cert")
	keyPath = filepath.Join(certDir, "ssl.key")

	if !certs.FilesExist(certPath, keyPath) {
		if hostname == "" {
			hostname = defaultHostname
		}
		slog.Info("generating self-signed certificate", "hostname", hostname)
		if err = certs.GenerateSelfSigned(hostname, certPath, keyPath); err != nil {
			return "", "", fmt.Errorf("generating certificate: %w", err)
		}
	}

	srv.TLSConfig = certs.SecureTLSConfig()
	return certPath, keyPath, nil
}
