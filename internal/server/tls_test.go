package server

import "testing"

func TestCertificateHostnameStripsPublishedPort(t *testing.T) {
	tests := map[string]string{
		"registry.example.com":      "registry.example.com",
		"registry.example.com:8443": "registry.example.com",
		"192.0.2.1:9443":            "192.0.2.1",
		"[2001:db8::1]:8443":        "2001:db8::1",
		"2001:db8::1":               "2001:db8::1",
	}
	for input, want := range tests {
		if got := certificateHostname(input); got != want {
			t.Errorf("certificateHostname(%q) = %q, want %q", input, got, want)
		}
	}
}
