package config

import (
	"crypto/x509"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
)

// certExtensions lists file extensions treated as certificate/key material.
var certExtensions = []string{".crt", ".cert", ".key", ".pem"}

// LoadCerts walks dir and returns the raw contents of all certificate and key
// files (*.crt, *.cert, *.key, *.pem) keyed by their path relative to dir.
// If dir does not exist, an empty map is returned with no error.
//
// Raw bytes are returned rather than parsed x509.Certificate values because the
// loaded files may contain a mix of PEM-encoded certificates, private keys, and
// other key material. Callers that need parsed certificates (e.g.,
// BuildTLSCertPool) handle PEM decoding themselves.
func LoadCerts(dir string) (map[string][]byte, error) {
	certs := make(map[string][]byte)

	info, err := os.Stat(dir)
	if os.IsNotExist(err) {
		return certs, nil
	}
	if err != nil {
		return nil, fmt.Errorf("certs: stat %s: %w", dir, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("certs: %s is not a directory", dir)
	}

	err = filepath.WalkDir(dir, func(path string, d os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			return nil
		}
		ext := strings.ToLower(filepath.Ext(d.Name()))
		if !slices.Contains(certExtensions, ext) {
			return nil
		}
		data, readErr := os.ReadFile(path) //nolint:gosec // walking user-provided config dir
		if readErr != nil {
			return fmt.Errorf("certs: read %s: %w", path, readErr)
		}
		relativePath, relPathErr := filepath.Rel(dir, path)
		if relPathErr != nil {
			return fmt.Errorf("certs: rel path %s: %w", path, relPathErr)
		}
		certs[relativePath] = data
		return nil
	})
	if err != nil {
		return nil, err
	}
	return certs, nil
}

// BuildTLSCertPool returns a certificate pool containing the system roots
// plus any PEM certificates from the certs map whose relative path starts
// with "extra_ca_certs/".
func BuildTLSCertPool(certs map[string][]byte) (*x509.CertPool, error) {
	pool, err := x509.SystemCertPool()
	if err != nil {
		pool = x509.NewCertPool()
	}
	for relativePath, data := range certs {
		if strings.HasPrefix(relativePath, "extra_ca_certs/") || strings.HasPrefix(relativePath, "extra_ca_certs\\") {
			if !pool.AppendCertsFromPEM(data) {
				return nil, fmt.Errorf("certs: failed to parse PEM from %s", relativePath)
			}
		}
	}
	return pool, nil
}
