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
		{"+8443", true},
		{" 8443", true},
		{"8443 ", true},
		{"８４４３", true},
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

func TestValidateInitUsername(t *testing.T) {
	tests := []struct {
		username string
		wantErr  bool
	}{
		{"admin", false},
		{"custom-admin", false},
		{"custom_admin.example", false},
		{"a", true},
		{"Admin", true},
		{"bad user", true},
		{"bad\nuser", true},
		{"-admin", true},
		{"admin-", true},
	}
	for _, test := range tests {
		t.Run(test.username, func(t *testing.T) {
			err := ValidateInitUsername(test.username)
			if (err != nil) != test.wantErr {
				t.Errorf("ValidateInitUsername(%q) error = %v, wantErr %v", test.username, err, test.wantErr)
			}
		})
	}
}

func TestValidateInitPassword(t *testing.T) {
	if err := ValidateInitPassword(" leading and trailing "); err != nil {
		t.Fatalf("whitespace should be preserved and accepted: %v", err)
	}
	if err := ValidateInitPassword(""); err == nil {
		t.Fatal("empty password should be rejected")
	}
	if err := ValidateInitPassword(string(make([]byte, 73))); err == nil {
		t.Fatal("password over bcrypt limit should be rejected")
	}
}
