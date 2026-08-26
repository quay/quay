package encryptedfield

import (
	"encoding/hex"
	"errors"
	"fmt"
	"math/big"

	"github.com/google/uuid"
)

const aesKeySize = 32

var (
	// ErrInvalidKey indicates a database secret key cannot be converted to an AES key.
	ErrInvalidKey = errors.New("encryptedfield: invalid key")
	// ErrInvalidFormat indicates an encrypted value is not a supported v0 encoded payload.
	ErrInvalidFormat = errors.New("encryptedfield: invalid format")
	// ErrUnsupportedVersion indicates an encrypted value uses a version this package cannot decrypt.
	ErrUnsupportedVersion = errors.New("encryptedfield: unsupported version")
	// ErrDecrypt indicates authenticated decryption failed.
	ErrDecrypt = errors.New("encryptedfield: decrypt")
)

// ConvertSecretKey converts Quay's Python DATABASE_SECRET_KEY formats to a 32-byte AES key.
func ConvertSecretKey(secret string) ([]byte, error) {
	source, err := secretSourceBytes(secret)
	if err != nil {
		return nil, err
	}
	if len(source) == 0 {
		return nil, ErrInvalidKey
	}

	key := make([]byte, aesKeySize)
	for i := range key {
		key[i] = source[i%len(source)]
	}

	return key, nil
}

func secretSourceBytes(secret string) ([]byte, error) {
	if i, ok := new(big.Int).SetString(secret, 10); ok {
		hexText := fmt.Sprintf("%02x", i)
		if source, err := hex.DecodeString(hexText); err == nil {
			return source, nil
		}
	}

	if id, err := uuid.Parse(secret); err == nil {
		source := make([]byte, 16)
		copy(source, id[:])
		return source, nil
	}

	var source []byte
	for _, r := range secret {
		if r > 0xff {
			return nil, ErrInvalidKey
		}
		source = append(source, byte(r)) // #nosec G115 -- Python compatibility rejects runes above one byte.
	}

	return source, nil
}
