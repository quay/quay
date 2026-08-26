package jwtauth

import (
	"bytes"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/go-jose/go-jose/v4"
)

const (
	// KeyFileName is the native v3 registry token signing key filename.
	KeyFileName = "registry-jwt.pem"
	keyBits     = 2048
)

// LoadOrCreatePrivateKey loads the persisted registry signing key, creating it
// once for a fresh v3 installation when it does not exist.
func LoadOrCreatePrivateKey(dataDir string) (*rsa.PrivateKey, error) {
	path := filepath.Join(dataDir, KeyFileName)
	key, err := LoadPrivateKey(path)
	if err == nil {
		return key, nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}

	key, err = rsa.GenerateKey(rand.Reader, keyBits)
	if err != nil {
		return nil, fmt.Errorf("generate registry JWT signing key: %w", err)
	}
	if err := WritePrivateKey(path, key); err != nil {
		if errors.Is(err, os.ErrExist) {
			return LoadPrivateKey(path)
		}
		return nil, err
	}
	return key, nil
}

// LoadPrivateKey reads an RSA private key from PKCS#1 or PKCS#8 PEM.
func LoadPrivateKey(path string) (*rsa.PrivateKey, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, fmt.Errorf("stat registry JWT signing key %s: %w", path, err)
	}
	if !info.Mode().IsRegular() {
		return nil, fmt.Errorf("registry JWT signing key %s must be a regular file", path)
	}
	if info.Mode().Perm()&0o077 != 0 {
		return nil, fmt.Errorf("registry JWT signing key %s has insecure permissions %04o", path, info.Mode().Perm())
	}
	file, err := os.Open(path) //nolint:gosec // private key path is controlled by registry configuration
	if err != nil {
		return nil, fmt.Errorf("open registry JWT signing key %s: %w", path, err)
	}
	defer func() { _ = file.Close() }()
	openedInfo, err := file.Stat()
	if err != nil {
		return nil, fmt.Errorf("stat open registry JWT signing key %s: %w", path, err)
	}
	if !openedInfo.Mode().IsRegular() || openedInfo.Mode().Perm()&0o077 != 0 || !os.SameFile(info, openedInfo) {
		return nil, fmt.Errorf("registry JWT signing key %s changed during validation", path)
	}
	data, err := io.ReadAll(file)
	if err != nil {
		return nil, fmt.Errorf("read registry JWT signing key %s: %w", path, err)
	}
	key, err := ParsePrivateKey(data)
	if err != nil {
		return nil, fmt.Errorf("parse registry JWT signing key %s: %w", path, err)
	}
	return key, nil
}

// ParsePrivateKey parses an RSA private key from one PKCS#1 or PKCS#8 PEM block.
func ParsePrivateKey(data []byte) (*rsa.PrivateKey, error) {
	block, rest := pem.Decode(data)
	if block == nil || len(bytes.TrimSpace(rest)) != 0 {
		return nil, fmt.Errorf("expected one PEM block")
	}

	if key, err := x509.ParsePKCS1PrivateKey(block.Bytes); err == nil {
		if err := key.Validate(); err != nil {
			return nil, fmt.Errorf("validate RSA private key: %w", err)
		}
		return key, nil
	}
	parsed, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	key, ok := parsed.(*rsa.PrivateKey)
	if !ok {
		return nil, fmt.Errorf("key is not RSA")
	}
	if err := key.Validate(); err != nil {
		return nil, fmt.Errorf("validate RSA private key: %w", err)
	}
	return key, nil
}

// WritePrivateKey atomically persists key without replacing existing material.
func WritePrivateKey(path string, key *rsa.PrivateKey) error {
	return persistPrivateKey(path, key, false)
}

// ReplacePrivateKey atomically replaces path with key using mode 0600.
func ReplacePrivateKey(path string, key *rsa.PrivateKey) error {
	return persistPrivateKey(path, key, true)
}

func persistPrivateKey(path string, key *rsa.PrivateKey, replace bool) error {
	if key == nil {
		return fmt.Errorf("nil registry JWT signing key")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
		return fmt.Errorf("create registry JWT key directory: %w", err)
	}

	temporary, err := os.CreateTemp(filepath.Dir(path), ".registry-jwt-*")
	if err != nil {
		return fmt.Errorf("create temporary registry JWT signing key: %w", err)
	}
	temporaryPath := temporary.Name()
	defer func() { _ = os.Remove(temporaryPath) }()
	if err := temporary.Chmod(0o600); err != nil {
		_ = temporary.Close()
		return fmt.Errorf("secure temporary registry JWT signing key: %w", err)
	}
	writeErr := pem.Encode(temporary, &pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
	syncErr := temporary.Sync()
	closeErr := temporary.Close()
	if err := errors.Join(writeErr, syncErr, closeErr); err != nil {
		return fmt.Errorf("write registry JWT signing key %s: %w", path, err)
	}
	if replace {
		if err := os.Rename(temporaryPath, path); err != nil {
			return fmt.Errorf("replace registry JWT signing key %s: %w", path, err)
		}
	} else {
		if err := os.Link(temporaryPath, path); err != nil {
			return fmt.Errorf("create registry JWT signing key %s: %w", path, err)
		}
		if err := os.Remove(temporaryPath); err != nil {
			return fmt.Errorf("remove temporary registry JWT signing key %s: %w", temporaryPath, err)
		}
	}
	temporaryPath = ""
	directory, err := os.Open(filepath.Dir(path)) //nolint:gosec // directory is controlled by registry configuration
	if err != nil {
		return fmt.Errorf("open registry JWT key directory: %w", err)
	}
	if err := errors.Join(directory.Sync(), directory.Close()); err != nil {
		return fmt.Errorf("sync registry JWT key directory: %w", err)
	}
	return nil
}

// KeyID returns the RFC 7638 SHA-256 thumbprint for key's public JWK.
func KeyID(key crypto.PublicKey) (string, error) {
	jwk := jose.JSONWebKey{Key: key}
	thumbprint, err := jwk.Thumbprint(crypto.SHA256)
	if err != nil {
		return "", fmt.Errorf("compute registry JWT key ID: %w", err)
	}
	return base64.RawURLEncoding.EncodeToString(thumbprint), nil
}

// PublicKeysEqual reports whether two public keys have identical PKIX encodings.
func PublicKeysEqual(a, b crypto.PublicKey) bool {
	aDER, aErr := x509.MarshalPKIXPublicKey(a)
	bDER, bErr := x509.MarshalPKIXPublicKey(b)
	return aErr == nil && bErr == nil && bytes.Equal(aDER, bDER)
}
