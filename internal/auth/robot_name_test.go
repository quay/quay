package auth

import (
	"strings"
	"testing"
)

func TestParseRobotUsername(t *testing.T) {
	tests := []struct {
		name          string
		username      string
		wantOwner     string
		wantShortname string
		wantOK        bool
	}{
		{
			name:          "valid",
			username:      "acme+deploy",
			wantOwner:     "acme",
			wantShortname: "deploy",
			wantOK:        true,
		},
		{
			name:     "missing plus",
			username: "acmedeploy",
			wantOK:   false,
		},
		{
			name:     "multiple plus",
			username: "acme+deploy+extra",
			wantOK:   false,
		},
		{
			name:     "empty owner",
			username: "+deploy",
			wantOK:   false,
		},
		{
			name:     "empty shortname",
			username: "acme+",
			wantOK:   false,
		},
		{
			name:     "uppercase owner",
			username: "Acme+deploy",
			wantOK:   false,
		},
		{
			name:     "short owner",
			username: "a+deploy",
			wantOK:   false,
		},
		{
			name:     "short shortname",
			username: "acme+d",
			wantOK:   false,
		},
		{
			name:          "minimum lengths",
			username:      "aa+bb",
			wantOwner:     "aa",
			wantShortname: "bb",
			wantOK:        true,
		},
		{
			name:          "maximum shortname length",
			username:      "acme+" + strings.Repeat("a", 255),
			wantOwner:     "acme",
			wantShortname: strings.Repeat("a", 255),
			wantOK:        true,
		},
		{
			name:     "long username",
			username: "acme+" + strings.Repeat("a", 256),
			wantOK:   false,
		},
		{
			name:     "SQL-ish syntax",
			username: "acme+deploy';drop",
			wantOK:   false,
		},
		{
			name:          "valid separators",
			username:      "acme-inc+deploy.01",
			wantOwner:     "acme-inc",
			wantShortname: "deploy.01",
			wantOK:        true,
		},
		{
			name:     "multiple plus separators",
			username: "acme++deploy",
			wantOK:   false,
		},
		{
			name:     "leading separator",
			username: "acme+.deploy",
			wantOK:   false,
		},
		{
			name:     "trailing separator",
			username: "acme+deploy-",
			wantOK:   false,
		},
		{
			name:     "repeated separator",
			username: "acme+deploy..prod",
			wantOK:   false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			owner, shortname, ok := parseRobotUsername(tt.username)

			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if owner != tt.wantOwner {
				t.Fatalf("owner = %q, want %q", owner, tt.wantOwner)
			}
			if shortname != tt.wantShortname {
				t.Fatalf("shortname = %q, want %q", shortname, tt.wantShortname)
			}
		})
	}
}

func TestIsASCII(t *testing.T) {
	tests := []struct {
		name string
		s    string
		want bool
	}{
		{
			name: "ASCII",
			s:    "abc123!@#",
			want: true,
		},
		{
			name: "non-ASCII",
			s:    "é",
			want: false,
		},
		{
			name: "invalid UTF-8",
			s:    string([]byte{0xff}),
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := isASCII(tt.s); got != tt.want {
				t.Fatalf("isASCII(%q) = %v, want %v", tt.s, got, tt.want)
			}
		})
	}
}
