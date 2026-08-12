package jwtauth

import (
	"crypto/rand"
	"crypto/rsa"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadOrCreatePrivateKeyPersistsOneRestrictedKey(t *testing.T) {
	dir := t.TempDir()
	first, err := LoadOrCreatePrivateKey(dir)
	require.NoError(t, err)
	second, err := LoadOrCreatePrivateKey(dir)
	require.NoError(t, err)
	assert.True(t, PublicKeysEqual(&first.PublicKey, &second.PublicKey))

	info, err := os.Stat(filepath.Join(dir, KeyFileName))
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o600), info.Mode().Perm())
}

func TestLoadPrivateKeyRejectsUnsafeFiles(t *testing.T) {
	dir := t.TempDir()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	target := filepath.Join(dir, "target.pem")
	require.NoError(t, WritePrivateKey(target, key))

	t.Run("group readable", func(t *testing.T) {
		path := filepath.Join(dir, "group-readable.pem")
		require.NoError(t, WritePrivateKey(path, key))
		require.NoError(t, os.Chmod(path, 0o640))

		_, err := LoadPrivateKey(path)

		assert.ErrorContains(t, err, "insecure permissions")
	})

	t.Run("symlink", func(t *testing.T) {
		path := filepath.Join(dir, "linked.pem")
		require.NoError(t, os.Symlink(target, path))

		_, err := LoadPrivateKey(path)

		assert.ErrorContains(t, err, "must be a regular file")
	})
}

func TestReplacePrivateKeyAtomicallyReplacesExistingKey(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, KeyFileName)
	first, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	second, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	require.NoError(t, WritePrivateKey(path, first))

	require.NoError(t, ReplacePrivateKey(path, second))
	loaded, err := LoadPrivateKey(path)

	require.NoError(t, err)
	assert.True(t, PublicKeysEqual(&second.PublicKey, &loaded.PublicKey))
}
