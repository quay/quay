package apptokenauthentication

import (
	"testing"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateAppTokenAuthentication(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		// Valid
		{name: "AuthenticationTypeOnMissingOtherValues", config: map[string]interface{}{"AUTHENTICATION_TYPE": "AppToken"}, want: "invalid"},
		{name: "AuthenticationFeatureOff", config: map[string]interface{}{"AUTHENTICATION_TYPE": "AppToken", "FEATURE_APP_SPECIFIC_TOKENS": false}, want: "invalid"},
		{name: "DirectLoginEnabled", config: map[string]interface{}{"AUTHENTICATION_TYPE": "AppToken", "FEATURE_APP_SPECIFIC_TOKENS": true, "FEATURE_DIRECT_LOGIN": true}, want: "invalid"},
		{name: "AuthenticationTypeOnFeatureOnDirectLoginOff", config: map[string]interface{}{"AUTHENTICATION_TYPE": "AppToken", "FEATURE_APP_SPECIFIC_TOKENS": true, "FEATURE_DIRECT_LOGIN": false}, want: "valid"},
		{name: "WrongAuthType", config: map[string]interface{}{"AUTHENTICATION_TYPE": "Database"}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewAppTokenAuthenticationFieldGroup(tt.config)
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
