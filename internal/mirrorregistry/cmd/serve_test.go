package cmd

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestServeHasNoBootstrapCredentialFlags(t *testing.T) {
	cmd := newServeCmd()
	assert.Nil(t, cmd.Flags.Lookup("admin-username"))
	assert.Nil(t, cmd.Flags.Lookup("init-password"))
	assert.Nil(t, cmd.Flags.Lookup("init-password-stdin"))
}

func TestServeDefaultHostnameIncludesListenPort(t *testing.T) {
	cmd := newServeCmd()
	assert.Equal(t, "localhost:8443", cmd.Flags.Lookup("hostname").DefValue)
}

func TestRegistryTLSHostnameRemovesOnlyPublicPort(t *testing.T) {
	tests := []struct {
		name, publicHostname, want string
	}{
		{name: "dns with port", publicHostname: "registry.example.com:9443", want: "registry.example.com"},
		{name: "dns without port", publicHostname: "registry.example.com", want: "registry.example.com"},
		{name: "ipv6 with port", publicHostname: "[2001:db8::1]:9443", want: "2001:db8::1"},
		{name: "ipv6 without port", publicHostname: "[2001:db8::1]", want: "2001:db8::1"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := registryTLSHostname(tt.publicHostname)
			assert.NoError(t, err)
			assert.Equal(t, tt.want, got)
		})
	}
}
