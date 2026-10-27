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

func TestResolvePublicHostname(t *testing.T) {
	tests := []struct {
		name, hostname, addr, want string
	}{
		{name: "bare hostname gets port from addr", hostname: "registry.example.com", addr: ":8443", want: "registry.example.com:8443"},
		{name: "explicit port preserved", hostname: "registry.example.com:9999", addr: ":8443", want: "registry.example.com:9999"},
		{name: "port 443 omitted", hostname: "registry.example.com", addr: ":443", want: "registry.example.com"},
		{name: "addr with bind address", hostname: "registry.example.com", addr: "0.0.0.0:8443", want: "registry.example.com:8443"},
		{name: "default flags unchanged", hostname: "localhost:8443", addr: ":8443", want: "localhost:8443"},
		{name: "ipv6 hostname gets port", hostname: "[2001:db8::1]", addr: ":8443", want: "[2001:db8::1]:8443"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, resolvePublicHostname(tt.hostname, tt.addr))
		})
	}
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
