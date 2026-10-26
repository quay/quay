package certs

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"slices"
	"testing"
	"time"
)

func TestGenerateSelfSigned_DNS(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if err := GenerateSelfSigned("registry.example.com", certPath, keyPath, filepath.Join(dir, "rootCA.pem")); err != nil {
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

	if err := GenerateSelfSigned("192.168.1.100", certPath, keyPath, filepath.Join(dir, "rootCA.pem")); err != nil {
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

	if err := GenerateSelfSigned("test.local", filepath.Join(dir, "cert.pem"), keyPath, filepath.Join(dir, "rootCA.pem")); err != nil {
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

func TestGenerateSelfSigned_LeafVerifiesAgainstCA(t *testing.T) {
	for _, hostname := range []string{"registry.example.com", "192.168.1.100"} {
		dir := generate(t, hostname)
		leaf := readCert(t, filepath.Join(dir, "ssl.cert"))

		if leaf.IsCA || !leaf.BasicConstraintsValid || leaf.KeyUsage&x509.KeyUsageCertSign != 0 {
			t.Errorf("%s: expected a CA:FALSE leaf without certificate signing key usage", hostname)
		}
		if _, err := leaf.Verify(x509.VerifyOptions{
			DNSName:   hostname,
			Roots:     poolOf(readCert(t, filepath.Join(dir, "rootCA.pem"))),
			KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		}); err != nil {
			t.Errorf("%s: expected leaf to verify against rootCA.pem: %v", hostname, err)
		}
	}
}

func TestGenerateSelfSigned_KeyCannotSignOtherHosts(t *testing.T) {
	dir := generate(t, "registry.example.com")
	cert := loadCert(t, filepath.Join(dir, "ssl.cert"), filepath.Join(dir, "ssl.key"))
	forged := signLeaf(t, cert.Leaf, cert.PrivateKey, "www.google.com")

	opts := x509.VerifyOptions{DNSName: "www.google.com", Roots: poolOf(cert.Leaf)}
	if _, err := forged.Verify(opts); err == nil {
		t.Error("expected a cert signed by ssl.key to be rejected by clients trusting ssl.cert")
	}
	// A server can present ssl.cert as an intermediate, so the chain
	// rootCA.pem -> ssl.cert -> forged must not verify either.
	opts.Roots = poolOf(readCert(t, filepath.Join(dir, "rootCA.pem")))
	opts.Intermediates = poolOf(cert.Leaf)
	if _, err := forged.Verify(opts); err == nil {
		t.Error("expected a cert signed by ssl.key to be rejected by clients trusting rootCA.pem")
	}
}

func TestGenerateSelfSigned_CAIsNameConstrained(t *testing.T) {
	for _, tc := range []struct{ hostname, other string }{
		{"registry.example.com", "www.google.com"},
		{"192.168.1.100", "192.168.1.101"},
	} {
		dir := generate(t, tc.hostname)
		ca := readCert(t, filepath.Join(dir, "rootCA.pem"))

		// The real CA key is discarded, so re-issue a CA with the same
		// constraints under a test key to check what clients would enforce.
		key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		if err != nil {
			t.Fatalf("generate key: %v", err)
		}
		template := *ca
		template.PublicKey = &key.PublicKey
		template.SubjectKeyId = nil
		der, err := x509.CreateCertificate(rand.Reader, &template, &template, &key.PublicKey, key)
		if err != nil {
			t.Fatalf("create CA: %v", err)
		}
		testCA, err := x509.ParseCertificate(der)
		if err != nil {
			t.Fatalf("parse CA: %v", err)
		}
		roots := poolOf(testCA)

		allowed := signLeaf(t, testCA, key, tc.hostname)
		if _, err := allowed.Verify(x509.VerifyOptions{DNSName: tc.hostname, Roots: roots}); err != nil {
			t.Fatalf("%s: expected a leaf for the registry hostname to verify: %v", tc.hostname, err)
		}
		forged := signLeaf(t, testCA, key, tc.other)
		if _, err := forged.Verify(x509.VerifyOptions{DNSName: tc.other, Roots: roots}); err == nil {
			t.Errorf("%s: expected name constraints to reject a leaf for %s", tc.hostname, tc.other)
		}
	}
}

func TestGenerateSelfSigned_CAKeyNotWritten(t *testing.T) {
	dir := generate(t, "registry.example.com")

	ca := readCert(t, filepath.Join(dir, "rootCA.pem"))
	if !ca.IsCA || ca.MaxPathLen != 0 || !ca.MaxPathLenZero || ca.KeyUsage&x509.KeyUsageCertSign == 0 {
		t.Errorf("expected a pathlen:0 signing CA, got IsCA=%v MaxPathLen=%d MaxPathLenZero=%v KeyUsage=%v",
			ca.IsCA, ca.MaxPathLen, ca.MaxPathLenZero, ca.KeyUsage)
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read dir: %v", err)
	}
	var names []string
	for _, e := range entries {
		names = append(names, e.Name())
	}
	if want := []string{"rootCA.pem", "ssl.cert", "ssl.key"}; !slices.Equal(names, want) {
		t.Errorf("files = %v, want %v", names, want)
	}
}

func TestFilesExist(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "cert.pem")
	keyPath := filepath.Join(dir, "key.pem")

	if FilesExist(certPath, keyPath) {
		t.Error("expected false before generation")
	}

	if err := GenerateSelfSigned("test.local", certPath, keyPath, filepath.Join(dir, "rootCA.pem")); err != nil {
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

func generate(t *testing.T, hostname string) string {
	t.Helper()
	dir := t.TempDir()
	if err := GenerateSelfSigned(hostname, filepath.Join(dir, "ssl.cert"), filepath.Join(dir, "ssl.key"), filepath.Join(dir, "rootCA.pem")); err != nil {
		t.Fatalf("generate: %v", err)
	}
	return dir
}

func readCert(t *testing.T, path string) *x509.Certificate {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read cert: %v", err)
	}
	block, _ := pem.Decode(data)
	if block == nil {
		t.Fatalf("no PEM block in %s", path)
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		t.Fatalf("parse %s: %v", path, err)
	}
	return cert
}

func poolOf(cert *x509.Certificate) *x509.CertPool {
	pool := x509.NewCertPool()
	pool.AddCert(cert)
	return pool
}

func signLeaf(t *testing.T, parent *x509.Certificate, parentKey any, hostname string) *x509.Certificate {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatalf("generate key: %v", err)
	}
	template := x509.Certificate{
		SerialNumber: big.NewInt(2),
		Subject:      pkix.Name{CommonName: hostname},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}
	if ip := net.ParseIP(hostname); ip != nil {
		template.IPAddresses = []net.IP{ip}
	} else {
		template.DNSNames = []string{hostname}
	}
	der, err := x509.CreateCertificate(rand.Reader, &template, parent, &key.PublicKey, parentKey)
	if err != nil {
		t.Fatalf("create leaf: %v", err)
	}
	cert, err := x509.ParseCertificate(der)
	if err != nil {
		t.Fatalf("parse leaf: %v", err)
	}
	return cert
}
