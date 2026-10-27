package cmd

import (
	"bytes"
	"context"
	"testing"

	"github.com/quay/quay/internal/installer"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUpgradeCmdDefaultsPreserveExistingInstallation(t *testing.T) {
	var captured *installer.Config
	cmd := newUpgradeCmdWithDeps(func(_ context.Context, cfg *installer.Config) int {
		captured = cfg
		return 0
	})

	code := cmd.Execute(t.Context(), nil)

	require.Equal(t, 0, code)
	require.NotNil(t, captured)
	assert.Empty(t, captured.Hostname, "hostname must be resolved from the existing unit")
	assert.Empty(t, captured.DataDir, "data dir must be resolved from the existing unit")
	assert.Empty(t, captured.Port, "port must be resolved from the existing unit")
	assert.Equal(t, installer.DefaultImage, captured.Image)
	assert.False(t, captured.InitPasswordSet)
}

func TestUpgradeCmdHasNoBootstrapCredentialFlags(t *testing.T) {
	cmd := newUpgradeCmdWithDeps(func(_ context.Context, _ *installer.Config) int { return 0 })

	assert.Nil(t, cmd.Flags.Lookup("init-user"))
	assert.Nil(t, cmd.Flags.Lookup("init-password"))
	assert.Nil(t, cmd.Flags.Lookup("init-password-stdin"))
}

func TestUpgradeCmdPassesOverrides(t *testing.T) {
	var captured *installer.Config
	cmd := newUpgradeCmdWithDeps(func(_ context.Context, cfg *installer.Config) int {
		captured = cfg
		return 0
	})

	code := cmd.Execute(t.Context(), []string{
		"-hostname=registry.example.com",
		"-data-dir=/srv/registry",
		"-port=9443",
		"-ssl-cert=/tmp/cert.pem",
		"-ssl-key=/tmp/key.pem",
		"-ssl-skip-hostname-verification",
		"-image-archive=/tmp/quay.tar",
	})

	require.Equal(t, 0, code)
	require.NotNil(t, captured)
	assert.Equal(t, "registry.example.com", captured.Hostname)
	assert.Equal(t, "/srv/registry", captured.DataDir)
	assert.Equal(t, "9443", captured.Port)
	assert.Equal(t, "/tmp/cert.pem", captured.SSLCert)
	assert.Equal(t, "/tmp/key.pem", captured.SSLKey)
	assert.True(t, captured.SSLSkipHostnameVerification)
	assert.Equal(t, "/tmp/quay.tar", captured.ImageArchive)
}

func TestUpgradeCmdRejectsPartialSSLFlags(t *testing.T) {
	ran := false
	cmd := newUpgradeCmdWithDeps(func(_ context.Context, _ *installer.Config) int {
		ran = true
		return 0
	})

	code := cmd.Execute(t.Context(), []string{"-ssl-cert=/tmp/cert.pem"})

	assert.Equal(t, 1, code)
	assert.False(t, ran)
}

func TestUpgradeCmdReturnsRunExitCode(t *testing.T) {
	cmd := newUpgradeCmdWithDeps(func(_ context.Context, _ *installer.Config) int { return 1 })

	assert.Equal(t, 1, cmd.Execute(t.Context(), nil))
}

func TestUpgradeCmdHelp(t *testing.T) {
	cmd := newUpgradeCmdWithDeps(func(_ context.Context, _ *installer.Config) int { return 0 })

	var buf bytes.Buffer
	cmd.Usage(&buf)

	for _, want := range []string{"usage: upgrade", "mirror-registry install", "-hostname", "-data-dir", "-port", "-ssl-cert", "-ssl-key", "-image-archive"} {
		assert.Contains(t, buf.String(), want)
	}
}

func TestInstallCmdDescribesFreshInstallOnly(t *testing.T) {
	cmd := newInstallCmd()

	var buf bytes.Buffer
	cmd.Usage(&buf)

	assert.Contains(t, buf.String(), "mirror-registry upgrade")
	assert.NotContains(t, cmd.Synopsis, "upgrade")
}
