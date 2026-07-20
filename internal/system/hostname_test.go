package system

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHostnameWithoutPort(t *testing.T) {
	tests := []struct {
		name, hostname, want string
	}{
		{name: "DNS with port", hostname: "registry.example.com:9443", want: "registry.example.com"},
		{name: "DNS without port", hostname: "registry.example.com", want: "registry.example.com"},
		{name: "IPv6 with port", hostname: "[2001:db8::1]:9443", want: "2001:db8::1"},
		{name: "bracketed IPv6 without port", hostname: "[2001:db8::1]", want: "2001:db8::1"},
		{name: "bare IPv6 without port", hostname: "2001:db8::1", want: "2001:db8::1"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, HostnameWithoutPort(tt.hostname))
		})
	}
}
