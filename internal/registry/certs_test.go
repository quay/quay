package registry

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"net"
	"os"
	"path/filepath"
	"testing"
)

func TestGenerateSelfSignedCert_DNS(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSignedCert("registry.example.com", certPath, keyPath); err != nil {
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

func TestGenerateSelfSignedCert_IP(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSignedCert("192.168.1.100", certPath, keyPath); err != nil {
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

func TestGenerateSelfSignedCert_KeyPermissions(t *testing.T) {
	dir := t.TempDir()
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSignedCert("test.local", filepath.Join(dir, "cert.pem"), keyPath); err != nil {
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

func TestCertFilesExist(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if CertFilesExist(certPath, keyPath) {
		t.Error("expected false before generation")
	}

	if err := GenerateSelfSignedCert("test.local", certPath, keyPath); err != nil {
		t.Fatalf("generate: %v", err)
	}

	if !CertFilesExist(certPath, keyPath) {
		t.Error("expected true after generation")
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
	parsed, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		t.Fatalf("parse x509: %v", err)
	}
	cert.Leaf = parsed

	return cert
}
