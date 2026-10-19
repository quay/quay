// Package certs provides self-signed TLS certificate generation and secure TLS configuration.
package certs

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"net"
	"os"
	"slices"
	"time"
)

// GenerateSelfSigned writes a TLS leaf certificate and key for the given
// hostname to certPath and keyPath, and the CA certificate that signed the leaf
// to caPath; clients trust caPath. The CA has pathlen 0 and is name-constrained
// to hostname (to IP SANs only, when hostname is an IP address), and its private
// key is discarded, so no other certificate can chain to it. Both certificates
// are valid for 10 years. If hostname is an IP address, it is used as an IP
// SAN; otherwise as a DNS SAN.
func GenerateSelfSigned(hostname, certPath, keyPath, caPath string) error {
	notBefore := time.Now()
	notAfter := notBefore.Add(10 * 365 * 24 * time.Hour)

	caKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return fmt.Errorf("generate CA key: %w", err)
	}

	caTemplate := x509.Certificate{
		Subject:                     pkix.Name{CommonName: hostname + " CA"},
		NotBefore:                   notBefore,
		NotAfter:                    notAfter,
		KeyUsage:                    x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid:       true,
		IsCA:                        true,
		MaxPathLen:                  0,
		MaxPathLenZero:              true,
		PermittedDNSDomainsCritical: true,
	}

	template := x509.Certificate{
		Subject:               pkix.Name{CommonName: hostname},
		NotBefore:             notBefore,
		NotAfter:              notAfter,
		KeyUsage:              x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		IsCA:                  false,
	}

	if ip := net.ParseIP(hostname); ip != nil {
		if ip4 := ip.To4(); ip4 != nil {
			ip = ip4
		}
		bits := len(ip) * 8
		caTemplate.PermittedIPRanges = []*net.IPNet{{IP: ip, Mask: net.CIDRMask(bits, bits)}}
		template.IPAddresses = []net.IP{ip}
	} else {
		caTemplate.PermittedDNSDomains = []string{hostname}
		template.DNSNames = []string{hostname}
	}

	caDER, err := x509.CreateCertificate(rand.Reader, &caTemplate, &caTemplate, &caKey.PublicKey, caKey)
	if err != nil {
		return fmt.Errorf("create CA certificate: %w", err)
	}
	ca, err := x509.ParseCertificate(caDER)
	if err != nil {
		return fmt.Errorf("parse CA certificate: %w", err)
	}

	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return fmt.Errorf("generate key: %w", err)
	}

	certDER, err := x509.CreateCertificate(rand.Reader, &template, ca, &key.PublicKey, caKey)
	if err != nil {
		return fmt.Errorf("create certificate: %w", err)
	}

	keyDER, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		return fmt.Errorf("marshal key: %w", err)
	}

	if err := writePEM(caPath, "CERTIFICATE", caDER, 0o644); err != nil {
		return fmt.Errorf("write CA cert: %w", err)
	}
	if err := writePEM(certPath, "CERTIFICATE", certDER, 0o600); err != nil {
		return fmt.Errorf("write cert: %w", err)
	}
	if err := writePEM(keyPath, "EC PRIVATE KEY", keyDER, 0o600); err != nil {
		return fmt.Errorf("write key: %w", err)
	}

	return nil
}

func writePEM(path, blockType string, der []byte, perm os.FileMode) error {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, perm) //nolint:gosec // path from caller
	if err != nil {
		return err
	}
	if err := pem.Encode(f, &pem.Block{Type: blockType, Bytes: der}); err != nil {
		_ = f.Close()
		return err
	}
	return f.Close()
}

// SecureTLSConfig returns a hardened TLS configuration with ECDHE-only cipher
// suites and modern curve preferences. The protocols parameter controls the
// minimum TLS version: if it contains only "TLSv1.3", MinVersion is set to
// TLS 1.3; otherwise MinVersion defaults to TLS 1.2.
func SecureTLSConfig(protocols []string) *tls.Config {
	minVersion := uint16(tls.VersionTLS12)
	if len(protocols) > 0 && !slices.Contains(protocols, "TLSv1.2") {
		minVersion = tls.VersionTLS13
	}

	return &tls.Config{ //nolint:gosec // minVersion is always TLS 1.2 or 1.3
		MinVersion: minVersion,
		CipherSuites: []uint16{
			tls.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
			tls.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
			tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
			tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
			tls.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256,
			tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256,
		},
		CurvePreferences: []tls.CurveID{
			tls.X25519,
			tls.CurveP256,
		},
	}
}

// FilesExist returns true if both cert and key files exist.
func FilesExist(certPath, keyPath string) bool {
	if _, err := os.Stat(certPath); err != nil {
		return false
	}
	if _, err := os.Stat(keyPath); err != nil {
		return false
	}
	return true
}
