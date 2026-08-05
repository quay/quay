package certs

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"net"
	"os"
	"path/filepath"
	"testing"
)

func TestGenerateSelfSigned_DNS(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSigned("registry.example.com", certPath, keyPath); err != nil {
		t.Fatalf("generate: %v", err)
	}

	cert := loadCert(t, certPath, keyPath)
	if len(cert.Leaf.DNSNames) != 1 || cert.Leaf.DNSNames[0] != "registry.example.com" {
		t.Errorf("expected DNS SAN 'registry.example.com', got %v", cert.Leaf.DNSNames)
	}
	if len(cert.Leaf.IPAddresses) != 0 {
		t.Errorf("expected no IP SANs, got %v", cert.Leaf.IPAddresses)
	}
}

func TestGenerateSelfSigned_IP(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSigned("192.168.1.100", certPath, keyPath); err != nil {
		t.Fatalf("generate: %v", err)
	}

	cert := loadCert(t, certPath, keyPath)
	if len(cert.Leaf.IPAddresses) != 1 || !cert.Leaf.IPAddresses[0].Equal(net.ParseIP("192.168.1.100")) {
		t.Errorf("expected IP SAN 192.168.1.100, got %v", cert.Leaf.IPAddresses)
	}
	if len(cert.Leaf.DNSNames) != 0 {
		t.Errorf("expected no DNS SANs, got %v", cert.Leaf.DNSNames)
	}
}

func TestGenerateSelfSigned_KeyPermissions(t *testing.T) {
	dir := t.TempDir()
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSigned("test.local", filepath.Join(dir, "cert.pem"), keyPath); err != nil {
		t.Fatalf("generate: %v", err)
	}

	info, err := os.Stat(keyPath)
	if err != nil {
		t.Fatalf("stat key: %v", err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Errorf("expected key permissions 0600, got %o", perm)
	}
}

func TestGenerateSelfSigned_IsCertificateAuthority(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSigned("registry.example.com", certPath, keyPath); err != nil {
		t.Fatalf("generate: %v", err)
	}

	cert := loadCert(t, certPath, keyPath)
	if !cert.Leaf.IsCA || !cert.Leaf.BasicConstraintsValid {
		t.Error("expected a valid CA certificate")
	}
	if cert.Leaf.KeyUsage&x509.KeyUsageCertSign == 0 {
		t.Error("expected certificate signing key usage")
	}
}

func TestFilesExist(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if FilesExist(certPath, keyPath) {
		t.Error("expected false before generation")
	}

	if err := GenerateSelfSigned("test.local", certPath, keyPath); err != nil {
		t.Fatalf("generate: %v", err)
	}

	if !FilesExist(certPath, keyPath) {
		t.Error("expected true after generation")
	}
}

func TestSecureTLSConfig_NilProtocols(t *testing.T) {
	cfg := SecureTLSConfig(nil)
	if cfg.MinVersion != tls.VersionTLS12 {
		t.Fatalf("MinVersion = %d, want TLS 1.2 (%d)", cfg.MinVersion, tls.VersionTLS12)
	}
}

func TestSecureTLSConfig_EmptyProtocols(t *testing.T) {
	cfg := SecureTLSConfig([]string{})
	if cfg.MinVersion != tls.VersionTLS12 {
		t.Fatalf("MinVersion = %d, want TLS 1.2 (%d)", cfg.MinVersion, tls.VersionTLS12)
	}
}

func TestSecureTLSConfig_TLS12And13(t *testing.T) {
	cfg := SecureTLSConfig([]string{"TLSv1.2", "TLSv1.3"})
	if cfg.MinVersion != tls.VersionTLS12 {
		t.Fatalf("MinVersion = %d, want TLS 1.2 (%d)", cfg.MinVersion, tls.VersionTLS12)
	}
}

func TestSecureTLSConfig_TLS13Only(t *testing.T) {
	cfg := SecureTLSConfig([]string{"TLSv1.3"})
	if cfg.MinVersion != tls.VersionTLS13 {
		t.Fatalf("MinVersion = %d, want TLS 1.3 (%d)", cfg.MinVersion, tls.VersionTLS13)
	}
}

func TestSecureTLSConfig_TLS12Only(t *testing.T) {
	cfg := SecureTLSConfig([]string{"TLSv1.2"})
	if cfg.MinVersion != tls.VersionTLS12 {
		t.Fatalf("MinVersion = %d, want TLS 1.2 (%d)", cfg.MinVersion, tls.VersionTLS12)
	}
}

func loadCert(t *testing.T, certPath, keyPath string) tls.Certificate {
	t.Helper()
	certPEM, err := os.ReadFile(certPath)
	if err != nil {
		t.Fatalf("read cert: %v", err)
	}
	keyPEM, err := os.ReadFile(keyPath)
	if err != nil {
		t.Fatalf("read key: %v", err)
	}

	cert, err := tls.X509KeyPair(certPEM, keyPEM)
	if err != nil {
		t.Fatalf("parse keypair: %v", err)
	}

	block, _ := pem.Decode(certPEM)
	if block == nil {
		t.Fatalf("failed to decode PEM block")
	}
	parsed, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		t.Fatalf("parse x509: %v", err)
	}
	cert.Leaf = parsed

	return cert
}
