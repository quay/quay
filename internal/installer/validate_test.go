package installer

import "testing"

func TestValidatePort(t *testing.T) {
	tests := []struct {
		port    string
		wantErr bool
	}{
		{"8443", false},
		{"1", false},
		{"65535", false},
		{"443", false},
		{"0", true},
		{"65536", true},
		{"-1", true},
		{"abc", true},
		{"", true},
		{"8443x", true},
	}
	for _, tt := range tests {
		t.Run(tt.port, func(t *testing.T) {
			err := ValidatePort(tt.port)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidatePort(%q) error = %v, wantErr %v", tt.port, err, tt.wantErr)
			}
		})
	}
}
