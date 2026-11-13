package shared

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"testing"
	"time"
)

func TestValidateIsHostname(t *testing.T) {
	var tests = []struct {
		name  string
		input string
		want  bool
	}{
		// Valid FQDNs
		{"fqdn", "registry.example.com", true},
		{"fqdnWithPort", "registry.example.com:8443", true},
		{"twoParts", "fakehost.com", true},
		{"twoParts with port", "fakehost.com:443", true},
		{"subdomains", "my.registry.example.com", true},
		{"hyphenated", "my-registry.example.com", true},
		{"hyphenatedWithPort", "my-registry.example.com:5000", true},
		{"localhost", "localhost", true},
		{"localhostWithPort", "localhost:8443", true},

		// Invalid: single-label hostnames (no dots, not localhost)
		{"singleLabel", "myregistry", false},
		{"singleLabelWithPort", "myregistry:8443", false},
		{"singleLabelHyphen", "my-registry", false},
		{"singleLabelHyphenWithPort", "my-registry:8443", false},

		// Invalid: bad characters
		{"invalidChars", "registry!.com", false},
		{"spaces", "registry .com", false},
		{"underscore", "my_registry.com", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ok, err := ValidateIsHostname(tt.input, "TEST_FIELD", "TestGroup")
			if ok != tt.want {
				t.Errorf("ValidateIsHostname(%q) = %v, want %v. Error: %s", tt.input, ok, tt.want, err.Message)
			}
		})
	}
}

// TestValidateCertPairWithHostname tests the Validate function.
func TestValidateCertPairWithHostname(t *testing.T) {
	cert, key := generateTestCertificate(t, "fakehost.com")

	ok, err := ValidateCertPairWithHostname(cert, key, "fakehost.com", "")
	if !ok {
		t.Error(err)
	}
}

func generateTestCertificate(t *testing.T, hostname string) ([]byte, []byte) {
	t.Helper()

	privateKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}

	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	if err != nil {
		t.Fatal(err)
	}

	template := &x509.Certificate{
		SerialNumber: serialNumber,
		Subject:      pkix.Name{CommonName: hostname},
		DNSNames:     []string{hostname},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().Add(time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}

	certificateDER, err := x509.CreateCertificate(
		rand.Reader,
		template,
		template,
		&privateKey.PublicKey,
		privateKey,
	)
	if err != nil {
		t.Fatal(err)
	}

	privateKeyDER, err := x509.MarshalPKCS8PrivateKey(privateKey)
	if err != nil {
		t.Fatal(err)
	}

	certificatePEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certificateDER})
	privateKeyPEM := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privateKeyDER})
	return certificatePEM, privateKeyPEM
}
