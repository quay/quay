package hostsettings

import (
	"testing"
)

// TestValidateHostSettings tests the Validate function
func TestValidateHostSettings(t *testing.T) {
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{{
		config: map[string]interface{}{"PREFERRED_URL_SCHEME": "badURLScheme"},
		name:   "BadURLScheme",
		want:   "invalid",
	}}
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewHostSettingsFieldGroup(tt.config)
			if err != nil && tt.want != "typeError" {
				t.Errorf("Expected %s. Received %s", tt.want, err.Error())
			}

			validationErrors := fg.Validate()

			// Get result type
			received := ""
			if len(validationErrors) == 0 {
				received = "valid"
			} else {
				received = "invalid"
			}

			// Compare with expected
			if tt.want != received {
				t.Errorf("Expected %s. Received %s", tt.want, received)
			}

		})
	}
}
