package system

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHostnameWithoutPort(t *testing.T) {
	tests := []struct {
		name, hostname, want string
		wantErr              bool
	}{
		{name: "DNS with port", hostname: "registry.example.com:9443", want: "registry.example.com"},
		{name: "DNS without port", hostname: "registry.example.com", want: "registry.example.com"},
		{name: "IPv6 with port", hostname: "[2001:db8::1]:9443", want: "2001:db8::1"},
		{name: "bracketed IPv6 without port", hostname: "[2001:db8::1]", want: "2001:db8::1"},
		{name: "bare IPv6 without port", hostname: "2001:db8::1", want: "2001:db8::1"},
		{name: "empty brackets", hostname: "[]", wantErr: true},
		{name: "missing closing bracket", hostname: "[2001:db8::1", wantErr: true},
		{name: "missing opening bracket", hostname: "2001:db8::1]", wantErr: true},
		{name: "stray bracket", hostname: "registry].example.com", wantErr: true},
		{name: "stray closing bracket with port", hostname: "registry].example.com:9443", wantErr: true},
		{name: "stray opening bracket with port", hostname: "registry[.example.com:9443", wantErr: true},
		{name: "bracketed DNS with port", hostname: "[registry.example.com]:9443", wantErr: true},
		{name: "invalid bracketed IPv6 with port", hostname: "[2001:db8::zz]:9443", wantErr: true},
		{name: "non-numeric port", hostname: "registry.example.com:https", wantErr: true},
		{name: "out-of-range port", hostname: "registry.example.com:65536", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := HostnameWithoutPort(tt.hostname)
			if tt.wantErr {
				assert.Error(t, err)
				return
			}
			assert.NoError(t, err)
			assert.Equal(t, tt.want, got)
		})
	}
}
