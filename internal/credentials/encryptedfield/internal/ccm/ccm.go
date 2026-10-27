// SPDX-License-Identifier: MIT

// Package ccm implements Counter with CBC-MAC (CCM) AEAD for encrypted fields.
//
// This package is copied or adapted from Pion DTLS pkg/crypto/ccm and kept
// internal to avoid adding Pion DTLS as a module dependency.
package ccm

import (
	"crypto/cipher"
	"crypto/subtle"
	"encoding/binary"
	"errors"
	"math"
)

const (
	blockSize     = 16
	minNonceSize  = 7
	maxNonceSize  = 13
	maxLengthSize = 8
)

var (
	errInvalidBlockSize = errors.New("ccm: invalid block size")
	errInvalidTagSize   = errors.New("ccm: invalid tag size")
	errInvalidNonceSize = errors.New("ccm: invalid nonce size")
	errMessageTooLarge  = errors.New("ccm: message too large")
	errAuth             = errors.New("ccm: message authentication failed")
)

type ccm struct {
	block      cipher.Block
	tagSize    int
	nonceSize  int
	lengthSize int
}

// NewCCM returns a CCM AEAD for the given AES block cipher, tag size, and nonce size.
func NewCCM(b cipher.Block, tagSize, nonceSize int) (cipher.AEAD, error) {
	if b.BlockSize() != blockSize {
		return nil, errInvalidBlockSize
	}
	if tagSize < 4 || tagSize > 16 || tagSize%2 != 0 {
		return nil, errInvalidTagSize
	}
	if nonceSize < minNonceSize || nonceSize > maxNonceSize {
		return nil, errInvalidNonceSize
	}

	return &ccm{
		block:      b,
		tagSize:    tagSize,
		nonceSize:  nonceSize,
		lengthSize: blockSize - 1 - nonceSize,
	}, nil
}

func (c *ccm) NonceSize() int {
	return c.nonceSize
}

func (c *ccm) Overhead() int {
	return c.tagSize
}

func (c *ccm) Seal(dst, nonce, plaintext, additionalData []byte) []byte {
	if len(nonce) != c.nonceSize {
		panic(errInvalidNonceSize)
	}
	if !c.validPayloadSize(len(plaintext)) {
		panic(errMessageTooLarge)
	}

	ret, out := sliceForAppend(dst, len(plaintext)+c.tagSize)

	tag := c.auth(nonce, plaintext, additionalData)
	c.crypt(out[:len(plaintext)], plaintext, nonce, 1)
	c.maskTag(tag, nonce)
	copy(out[len(plaintext):], tag)

	return ret
}

func (c *ccm) Open(dst, nonce, ciphertext, additionalData []byte) ([]byte, error) {
	if len(nonce) != c.nonceSize {
		return nil, errInvalidNonceSize
	}
	if len(ciphertext) < c.tagSize {
		return nil, errAuth
	}

	payloadSize := len(ciphertext) - c.tagSize
	if !c.validPayloadSize(payloadSize) {
		return nil, errMessageTooLarge
	}

	ret, out := sliceForAppend(dst, payloadSize)
	c.crypt(out, ciphertext[:payloadSize], nonce, 1)

	tag := c.auth(nonce, out, additionalData)
	c.maskTag(tag, nonce)
	if subtle.ConstantTimeCompare(tag, ciphertext[payloadSize:]) != 1 {
		clear(out)
		return nil, errAuth
	}

	return ret, nil
}

func (c *ccm) auth(nonce, plaintext, additionalData []byte) []byte {
	var mac [blockSize]byte
	var b0 [blockSize]byte

	b0[0] = byte(c.lengthSize - 1)      // #nosec G115 -- lengthSize is derived from validated nonceSize.
	b0[0] |= byte((c.tagSize-2)/2) << 3 // #nosec G115 -- tagSize is validated to the CCM range.
	if len(additionalData) > 0 {
		b0[0] |= 1 << 6
	}
	copy(b0[1:], nonce)
	c.putLength(b0[blockSize-c.lengthSize:], uint64(len(plaintext)))

	c.block.Encrypt(mac[:], b0[:])

	if len(additionalData) > 0 {
		c.updateAuth(&mac, formatAdditionalData(additionalData))
	}
	c.updateAuth(&mac, plaintext)

	tag := make([]byte, c.tagSize)
	copy(tag, mac[:])
	return tag
}

func (c *ccm) updateAuth(mac *[blockSize]byte, data []byte) {
	for len(data) >= blockSize {
		xorBlock(mac[:], data[:blockSize])
		c.block.Encrypt(mac[:], mac[:])
		data = data[blockSize:]
	}

	if len(data) > 0 {
		var padded [blockSize]byte
		copy(padded[:], data)
		xorBlock(mac[:], padded[:])
		c.block.Encrypt(mac[:], mac[:])
	}
}

func (c *ccm) crypt(dst, src, nonce []byte, counter uint64) {
	var counterBlock [blockSize]byte
	var streamBlock [blockSize]byte

	for len(src) > 0 {
		c.counterBlock(counterBlock[:], nonce, counter)
		c.block.Encrypt(streamBlock[:], counterBlock[:])

		n := blockSize
		if len(src) < n {
			n = len(src)
		}
		for i := range n {
			dst[i] = src[i] ^ streamBlock[i]
		}

		dst = dst[n:]
		src = src[n:]
		counter++
	}
}

func (c *ccm) maskTag(tag, nonce []byte) {
	var counterBlock [blockSize]byte
	var streamBlock [blockSize]byte

	c.counterBlock(counterBlock[:], nonce, 0)
	c.block.Encrypt(streamBlock[:], counterBlock[:])
	xorBlock(tag, streamBlock[:len(tag)])
}

func (c *ccm) counterBlock(out, nonce []byte, counter uint64) {
	clear(out)
	out[0] = byte(c.lengthSize - 1) // #nosec G115 -- lengthSize is derived from validated nonceSize.
	copy(out[1:], nonce)
	c.putLength(out[blockSize-c.lengthSize:], counter)
}

func (c *ccm) putLength(out []byte, n uint64) {
	for i := len(out) - 1; i >= 0; i-- {
		out[i] = byte(n)
		n >>= 8
	}
}

func (c *ccm) validPayloadSize(size int) bool {
	if c.lengthSize == maxLengthSize {
		return true
	}

	return uint64(size) < (uint64(1) << (8 * c.lengthSize)) // #nosec G115 -- len-derived sizes are non-negative.
}

func formatAdditionalData(additionalData []byte) []byte {
	size := len(additionalData)
	switch {
	case size < 0xff00:
		out := make([]byte, 2+size)
		binary.BigEndian.PutUint16(out, uint16(size))
		copy(out[2:], additionalData)
		return out
	case uint64(size) <= math.MaxUint32:
		out := make([]byte, 6+size)
		out[0] = 0xff
		out[1] = 0xfe
		binary.BigEndian.PutUint32(out[2:], uint32(size))
		copy(out[6:], additionalData)
		return out
	default:
		out := make([]byte, 10+size)
		out[0] = 0xff
		out[1] = 0xff
		binary.BigEndian.PutUint64(out[2:], uint64(size))
		copy(out[10:], additionalData)
		return out
	}
}

func xorBlock(dst, src []byte) {
	for i := range dst {
		dst[i] ^= src[i]
	}
}

func sliceForAppend(in []byte, n int) (head, tail []byte) {
	if total := len(in) + n; cap(in) >= total {
		head = in[:total]
	} else {
		head = make([]byte, total)
		copy(head, in)
	}
	tail = head[len(in):]
	return head, tail
}
