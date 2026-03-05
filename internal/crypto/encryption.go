package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"math/big"
	"regexp"
	"strings"

	"golang.org/x/crypto/hkdf"
)

const (
	separator    = "$$"
	gcmNonceSize = 12

	// Protocol constants — must match Python's values exactly.
	hkdfSalt = "quay-field-encryption-v1"
	hkdfInfo = "aes-256-gcm"
)

var uuidRegex = regexp.MustCompile(
	`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`,
)

// NormalizeSecretKey converts a DATABASE_SECRET_KEY config value into raw bytes,
// matching Python's _normalize_secret_key() behavior:
//  1. Try parsing as a decimal integer → big-endian bytes
//  2. Try parsing as a UUID → 16 raw bytes
//  3. Fallback → ord() of each character (single-byte codepoints)
func NormalizeSecretKey(configKey string) ([]byte, error) {
	// Try integer
	n := new(big.Int)
	if _, ok := n.SetString(configKey, 10); ok {
		b := n.Bytes()
		if len(b) > 0 {
			return b, nil
		}
	}

	// Try UUID
	if uuidRegex.MatchString(configKey) {
		hex := strings.ReplaceAll(configKey, "-", "")
		b := new(big.Int)
		b.SetString(hex, 16)
		raw := b.Bytes()
		// Pad to 16 bytes (UUID is always 128 bits)
		if len(raw) < 16 {
			padded := make([]byte, 16)
			copy(padded[16-len(raw):], raw)
			raw = padded
		}
		return raw, nil
	}

	// Fallback: ord() of each character (matching Python's map(ord, ...))
	raw := make([]byte, len(configKey))
	for i := 0; i < len(configKey); i++ {
		raw[i] = configKey[i]
	}
	if len(raw) == 0 {
		return nil, errors.New("secret key must not be empty")
	}
	return raw, nil
}

// DeriveKey derives a 32-byte AES-256 key using HKDF-SHA256.
// Produces identical output to Python's derive_key_hkdf().
func DeriveKey(configKey string) ([]byte, error) {
	raw, err := NormalizeSecretKey(configKey)
	if err != nil {
		return nil, err
	}
	r := hkdf.New(sha256.New, raw, []byte(hkdfSalt), []byte(hkdfInfo))
	key := make([]byte, 32)
	if _, err := io.ReadFull(r, key); err != nil {
		return nil, fmt.Errorf("hkdf derive: %w", err)
	}
	return key, nil
}

// Encrypt encrypts plaintext using AES-256-GCM and returns a v1-prefixed string.
func Encrypt(configKey string, plaintext string) (string, error) {
	key, err := DeriveKey(configKey)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcmNonceSize)
	if _, err := rand.Read(nonce); err != nil {
		return "", err
	}

	// Seal appends ciphertext+tag after nonce
	sealed := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
	encoded := base64.StdEncoding.EncodeToString(sealed)
	return "v1" + separator + encoded, nil
}

// Decrypt decrypts a v1-prefixed encrypted value. Returns an error for v0 values.
func Decrypt(configKey string, value string) (string, error) {
	prefix, data, ok := strings.Cut(value, separator)
	if !ok {
		return "", errors.New("invalid encrypted value: missing separator")
	}
	if prefix != "v1" {
		return "", fmt.Errorf("unsupported version prefix: %s (only v1 is supported)", prefix)
	}

	key, err := DeriveKey(configKey)
	if err != nil {
		return "", err
	}

	decoded, err := base64.StdEncoding.DecodeString(data)
	if err != nil {
		return "", fmt.Errorf("base64 decode: %w", err)
	}
	if len(decoded) < gcmNonceSize {
		return "", errors.New("ciphertext too short")
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := decoded[:gcmNonceSize]
	ct := decoded[gcmNonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ct, nil)
	if err != nil {
		return "", fmt.Errorf("decrypt: %w", err)
	}
	return string(plaintext), nil
}

// CheckV0Rows is a placeholder for the startup gate that would reject v0-encrypted
// rows at Go service startup. In production this would query each encrypted table/column.
var EncryptedFields = []struct {
	Table  string
	Column string
}{
	{"robotaccounttoken", "token"},
	{"accesstoken", "token_code"},
	{"appspecificauthtoken", "token_secret"},
	{"repositorybuildtrigger", "secure_auth_token"},
	{"repositorybuildtrigger", "secure_private_key"},
	{"oauthapplication", "secure_client_secret"},
	{"repomirrorconfig", "external_registry_username"},
	{"repomirrorconfig", "external_registry_password"},
	{"orgmirrorconfig", "external_registry_username"},
	{"orgmirrorconfig", "external_registry_password"},
	{"proxycacheconfig", "upstream_registry_username"},
	{"proxycacheconfig", "upstream_registry_password"},
}
