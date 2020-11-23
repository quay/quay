package ldap

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateLDAP tests the Validate function
func TestValidateLDAP(t *testing.T) {
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		{
			name:   "wrongAuthType",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "Database"},
			want:   "valid",
		},
		{
			name:   "noValidAuthSettings",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "LDAP"},
			want:   "invalid",
		},
		{
			name: "validAuthSettings",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "LDAP",
				"LDAP_URI":          "ldap://ldap.forumsys.com",
				"LDAP_BASE_DN":      []interface{}{"dc=example", "dc=com"},
				"LDAP_ADMIN_DN":     "cn=read-only-admin,dc=example,dc=com",
				"LDAP_ADMIN_PASSWD": "password",
				"LDAP_USER_RDN":     []interface{}{},
				"LDAP_USER_FILTER":  "(dc=example)",
			},
			want: "valid",
		},
		{
			name: "invalidPassword",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "LDAP",
				"LDAP_URI":          "ldap://ldap.forumsys.com",
				"LDAP_BASE_DN":      []interface{}{"dc=example", "dc=com"},
				"LDAP_ADMIN_DN":     "cn=read-only-admin,dc=example,dc=com",
				"LDAP_ADMIN_PASSWD": "passwo",
				"LDAP_USER_RDN":     []interface{}{},
				"LDAP_USER_FILTER":  "(CN=hey)",
			},
			want: "invalid",
		},
		{
			name: "userExists",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "LDAP",
				"LDAP_URI":          "ldap://ldap.forumsys.com",
				"LDAP_BASE_DN":      []interface{}{"dc=example", "dc=com"},
				"LDAP_ADMIN_DN":     "cn=read-only-admin,dc=example,dc=com",
				"LDAP_ADMIN_PASSWD": "password",
				"LDAP_USER_RDN":     []interface{}{},
				"LDAP_USER_FILTER":  "",
			},
			want: "valid",
		},
	}
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewLDAPFieldGroup(tt.config)
			if err != nil && tt.want != "typeError" {
				t.Errorf("Expected %s. Received %s", tt.want, err.Error())
			}

			opts := shared.Options{}

			validationErrors := fg.Validate(opts)

			// Get result type
			received := ""
			if len(validationErrors) == 0 {
				received = "valid"
			} else {
				received = "invalid"
			}

			// Compare with expected
			if tt.want != received {
				for _, e := range validationErrors {
					t.Log(e)
				}
				t.Errorf("Expected %s. Received %s", tt.want, received)
			}

		})

	}
}
