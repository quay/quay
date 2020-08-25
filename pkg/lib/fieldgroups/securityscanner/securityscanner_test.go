package securityscanner

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateSecurityScanner(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		{name: "checkFeatureOff", config: map[string]interface{}{"FEATURE_SECURITY_SCANNER": false}, want: "valid"},
		{name: "checkFeatureOnMissigEndpoint", config: map[string]interface{}{"FEATURE_SECURITY_SCANNER": true}, want: "invalid"},
		{name: "checkFeatureOnGoodEnpointWProtocol", config: map[string]interface{}{"FEATURE_SECURITY_SCANNER": true, "SECURITY_SCANNER_ENDPOINT": "https://www.google.com:80"}, want: "valid"},
		{name: "checkFeatureOnBadEndpoint", config: map[string]interface{}{"FEATURE_SECURITY_SCANNER": true, "SECURITY_SCANNER_ENDPOINT": "http://thisisafakewebsiteandwillneverbecreated.com/"}, want: "invalid"},
		{name: "checkEndpointNotURL", config: map[string]interface{}{"FEATURE_SECURITY_SCANNER": true, "SECURITY_SCANNER_ENDPOINT": "not_a_url"}, want: "invalid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewSecurityScannerFieldGroup(tt.config)
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
