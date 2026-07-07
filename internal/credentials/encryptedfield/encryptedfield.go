// Package encryptedfield decrypts Python encrypted-field values stored in the Quay database.
package encryptedfield

import (
	"crypto/aes"
	"encoding/base64"
	"fmt"
	"strings"

	"github.com/quay/quay/internal/credentials/encryptedfield/internal/ccm"
)

const (
	separator = "$$"
	versionV0 = "v0"
	nonceSize = 13
	tagSize   = 16
)

// Decrypt decrypts a Python v0 encrypted-field value using the database secret key.
func Decrypt(secretKey, encryptedValue string) (string, error) {
	key, err := ConvertSecretKey(secretKey)
	if err != nil {
		return "", err
	}

	version, data, ok := strings.Cut(encryptedValue, separator)
	if !ok {
		return "", ErrInvalidFormat
	}
	if version != versionV0 {
		return "", ErrUnsupportedVersion
	}

	decoded, err := base64.StdEncoding.DecodeString(data)
	if err != nil {
		return "", fmt.Errorf("%w: base64", ErrInvalidFormat)
	}
	if len(decoded) < nonceSize+tagSize {
		return "", ErrInvalidFormat
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", fmt.Errorf("%w: aes", ErrInvalidKey)
	}
	aead, err := ccm.NewCCM(block, tagSize, nonceSize)
	if err != nil {
		return "", fmt.Errorf("%w: ccm", ErrInvalidKey)
	}

	nonce := decoded[:nonceSize]
	ciphertext := decoded[nonceSize:]
	plaintext, err := aead.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", ErrDecrypt
	}

	return string(plaintext), nil
}
