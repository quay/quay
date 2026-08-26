package ccm

import (
	"bytes"
	"crypto/aes"
	"testing"
)

func TestSealOpenRoundTrip(t *testing.T) {
	block, err := aes.NewCipher([]byte("test1234test1234test1234test1234"))
	if err != nil {
		t.Fatalf("aes.NewCipher: %v", err)
	}
	aead, err := NewCCM(block, 16, 13)
	if err != nil {
		t.Fatalf("NewCCM: %v", err)
	}

	nonce := []byte("1234567890123")
	plaintext := []byte("hello world")
	additionalData := []byte("metadata")

	ciphertext := aead.Seal(nil, nonce, plaintext, additionalData)
	if bytes.Equal(ciphertext[:len(plaintext)], plaintext) {
		t.Fatal("ciphertext payload matches plaintext")
	}

	got, err := aead.Open(nil, nonce, ciphertext, additionalData)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	if !bytes.Equal(got, plaintext) {
		t.Fatalf("plaintext = %q, want %q", got, plaintext)
	}
}

func TestOpenRejectsModifiedCiphertext(t *testing.T) {
	block, err := aes.NewCipher([]byte("test1234test1234test1234test1234"))
	if err != nil {
		t.Fatalf("aes.NewCipher: %v", err)
	}
	aead, err := NewCCM(block, 16, 13)
	if err != nil {
		t.Fatalf("NewCCM: %v", err)
	}

	nonce := []byte("1234567890123")
	ciphertext := aead.Seal(nil, nonce, []byte("hello world"), nil)
	ciphertext[0] ^= 0xff

	if _, err := aead.Open(nil, nonce, ciphertext, nil); err == nil {
		t.Fatal("err = nil, want authentication failure")
	}
}
