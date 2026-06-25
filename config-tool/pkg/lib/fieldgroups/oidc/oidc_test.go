package oidc

import (
	"testing"
)

func TestServiceID(t *testing.T) {
	tests := []struct {
		prefix string
		want   string
	}{
		{"AUTH0", "auth0"},
		{"ADFS", "adfs"},
		{"MY_CUSTOM", "my"},
		{"SOME_LONG_PREFIX", "some"},
		{"single", "single"},
		{"A_B_C", "a"},
	}

	for _, tt := range tests {
		t.Run(tt.prefix, func(t *testing.T) {
			p := &OIDCProvider{_Prefix: tt.prefix}
			got := p.ServiceID()
			if got != tt.want {
				t.Errorf("ServiceID() with prefix %q = %q, want %q", tt.prefix, got, tt.want)
			}
		})
	}
}

func TestRedirectURL(t *testing.T) {
	tests := []struct {
		name     string
		hostname string
		scheme   string
		prefix   string
		want     string
	}{
		{"standard", "registry.example.com", "https", "AUTH0", "https://registry.example.com/oauth2/auth0/callback"},
		{"http scheme", "registry.example.com", "http", "ADFS", "http://registry.example.com/oauth2/adfs/callback"},
		{"empty hostname", "", "https", "AUTH0", ""},
		{"default scheme", "registry.example.com", "", "AUTH0", "https://registry.example.com/oauth2/auth0/callback"},
		{"multi-part prefix", "registry.example.com", "https", "MY_CUSTOM", "https://registry.example.com/oauth2/my/callback"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fg := &OIDCFieldGroup{
				ServerHostname:     tt.hostname,
				PreferredUrlScheme: tt.scheme,
			}
			provider := &OIDCProvider{_Prefix: tt.prefix}
			got := fg.RedirectURL(provider)
			if got != tt.want {
				t.Errorf("RedirectURL() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestNewOIDCFieldGroupExtractsHostConfig(t *testing.T) {
	fullConfig := map[string]interface{}{
		"SERVER_HOSTNAME":      "registry.example.com",
		"PREFERRED_URL_SCHEME": "https",
		"AUTH0_LOGIN_CONFIG": map[string]interface{}{
			"OIDC_SERVER":   "https://auth0.example.com/",
			"CLIENT_ID":     "test-id",
			"CLIENT_SECRET": "test-secret",
			"SERVICE_NAME":  "Auth0",
		},
	}

	fg, err := NewOIDCFieldGroup(fullConfig)
	if err != nil {
		t.Fatalf("NewOIDCFieldGroup returned error: %v", err)
	}

	if fg.ServerHostname != "registry.example.com" {
		t.Errorf("ServerHostname = %q, want %q", fg.ServerHostname, "registry.example.com")
	}
	if fg.PreferredUrlScheme != "https" {
		t.Errorf("PreferredUrlScheme = %q, want %q", fg.PreferredUrlScheme, "https")
	}
	if len(fg.OIDCProviders) != 1 {
		t.Fatalf("expected 1 OIDC provider, got %d", len(fg.OIDCProviders))
	}
	if fg.OIDCProviders[0]._Prefix != "AUTH0" {
		t.Errorf("provider prefix = %q, want %q", fg.OIDCProviders[0]._Prefix, "AUTH0")
	}
}

func TestNewOIDCFieldGroupDefaultScheme(t *testing.T) {
	fullConfig := map[string]interface{}{
		"SERVER_HOSTNAME": "registry.example.com",
		// PREFERRED_URL_SCHEME intentionally omitted
	}

	fg, err := NewOIDCFieldGroup(fullConfig)
	if err != nil {
		t.Fatalf("NewOIDCFieldGroup returned error: %v", err)
	}

	if fg.ServerHostname != "registry.example.com" {
		t.Errorf("ServerHostname = %q, want %q", fg.ServerHostname, "registry.example.com")
	}
	// Default from struct tag should be "https"
	if fg.PreferredUrlScheme != "https" {
		t.Errorf("PreferredUrlScheme = %q, want %q (default)", fg.PreferredUrlScheme, "https")
	}
}
