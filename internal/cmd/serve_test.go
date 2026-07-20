package cmd

import (
	"testing"

	"github.com/quay/quay/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestConfigureStandaloneSuperuser(t *testing.T) {
	t.Run("defaults follow initialized user", func(t *testing.T) {
		resolved := &config.Resolved{Config: config.NewDefault("localhost", "/data/storage")}

		configureStandaloneSuperuser(resolved, "custom-admin")

		assert.Equal(t, []string{"custom-admin"}, resolved.Config.SuperUsers)
	})

	t.Run("explicit config remains authoritative", func(t *testing.T) {
		resolved := &config.Resolved{
			Config:   config.NewDefault("localhost", "/data/storage"),
			FromFile: true,
		}
		resolved.Config.SuperUsers = []string{"configured-admin"}

		configureStandaloneSuperuser(resolved, "database-user")

		assert.Equal(t, []string{"configured-admin"}, resolved.Config.SuperUsers)
	})
}

func TestServeHasNoBootstrapCredentialFlags(t *testing.T) {
	cmd := newServeCmd()
	assert.Nil(t, cmd.Flags.Lookup("admin-username"))
	assert.Nil(t, cmd.Flags.Lookup("init-password"))
	assert.Nil(t, cmd.Flags.Lookup("init-password-stdin"))
}
