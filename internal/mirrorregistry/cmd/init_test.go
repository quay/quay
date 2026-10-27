package cmd

import (
	"context"
	"strings"
	"testing"

	"github.com/quay/quay/internal/installer"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestReadInitPassword(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    string
		wantErr string
	}{
		{name: "pipe newline", input: "secret-password\n", want: "secret-password"},
		{name: "pipe CRLF", input: "secret-password\r\n", want: "secret-password"},
		{name: "no newline", input: "secret-password", want: "secret-password"},
		{name: "surrounding spaces preserved", input: "  secret password  \n", want: "  secret password  "},
		{name: "only one newline removed", input: "secret-password\n\n", want: "secret-password\n"},
		{name: "72 bytes plus CRLF", input: strings.Repeat("x", 72) + "\r\n", want: strings.Repeat("x", 72)},
		{name: "empty", input: "\n", wantErr: "must not be empty"},
		{name: "too long", input: strings.Repeat("x", 73), wantErr: "must not exceed 72 bytes"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got, err := readInitPassword(strings.NewReader(test.input))
			if test.wantErr != "" {
				require.ErrorContains(t, err, test.wantErr)
				return
			}
			require.NoError(t, err)
			assert.Equal(t, test.want, got)
		})
	}
}

func TestInitCommandReadsPasswordFromStdin(t *testing.T) {
	var got *installer.Config
	cmd := newInitCmdWithDeps(strings.NewReader("  chosen secret  \n"), func(_ context.Context, cfg *installer.Config) int {
		got = cfg
		return 0
	})

	require.Nil(t, cmd.Flags.Lookup("init-password"))
	require.NotNil(t, cmd.Flags.Lookup("init-password-stdin"))
	require.Equal(t, 0, cmd.Execute(t.Context(), []string{
		"-data-dir", "/tmp/quay-test",
		"-init-user", "custom-admin",
		"-init-password-stdin",
	}))
	require.NotNil(t, got)
	assert.Equal(t, "custom-admin", got.InitUser)
	assert.Equal(t, "  chosen secret  ", got.InitPassword)
	assert.True(t, got.InitPasswordSet)
}

func TestInstallCommandReadsPasswordFromStdin(t *testing.T) {
	var got *installer.Config
	cmd := newInstallCmdWithDeps(strings.NewReader("chosen-secret\n"), func(_ context.Context, cfg *installer.Config) int {
		got = cfg
		return 0
	})

	require.Nil(t, cmd.Flags.Lookup("init-password"))
	require.Equal(t, 0, cmd.Execute(t.Context(), []string{
		"-hostname", "registry.example.com",
		"-init-user", "custom-admin",
		"-init-password-stdin",
	}))
	require.NotNil(t, got)
	assert.Equal(t, "chosen-secret", got.InitPassword)
	assert.True(t, got.InitPasswordSet)
}
