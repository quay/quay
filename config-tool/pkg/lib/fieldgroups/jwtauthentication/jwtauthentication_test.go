package jwtauthentication

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateJWTAuthentication tests the Validate function
func TestValidateJWTAuthentication(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "WrongAuthType", config: map[string]interface{}{"AUTHENTICATION_TYPE": "Database"}, want: "valid"},
		{name: "MissingVerifyEndpoint", config: map[string]interface{}{"AUTHENTICATION_TYPE": "JWT"}, want: "invalid"},
		{name: "VerifyEndpointGood", config: map[string]interface{}{"AUTHENTICATION_TYPE": "JWT", "JWT_AUTH_ISSUER": "one", "JWT_VERIFY_ENDPOINT": "https://google.com"}, want: "valid"},
		{name: "VerifyEndpointBad", config: map[string]interface{}{"AUTHENTICATION_TYPE": "JWT", "JWT_AUTH_ISSUER": "one", "JWT_VERIFY_ENDPOINT": "notagoodendpoint"}, want: "invalid"},
		{name: "MissingAuthIssuer", config: map[string]interface{}{"AUTHENTICATION_TYPE": "JWT", "JWT_VERIFY_ENDPOINT": "https://google.com"}, want: "invalid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewJWTAuthenticationFieldGroup(tt.config)
			if err != nil && tt.want != "typeError" {
				t.Errorf("Expected %s. Received %s", tt.want, err.Error())
			}

			opts := shared.Options{
				Mode: "testing",
			}

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
				t.Errorf("Expected %s. Received %s", tt.want, received)
			}

		})
	}
}
