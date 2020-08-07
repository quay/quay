package signingengine

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateSigningEngine tests the Validate function
func TestValidateSigningEngine(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		{name: "checkFeatureOff", config: map[string]interface{}{"SIGNING_ENGINE": ""}, want: "valid"},
		{name: "checkFeatureValidEngineNoKeys", config: map[string]interface{}{"SIGNING_ENGINE": "gpg2"}, want: "invalid"},
		{name: "checkFeatureInvalidEngine", config: map[string]interface{}{"SIGNING_ENGINE": "notagoodengine"}, want: "invalid"},
		//{name: "checkFeatureValidEngineGoodKeys", config: map[string]interface{}{"SIGNING_ENGINE": "gpg2", "GPG2_PRIVATE_KEY_NAME": "hello", "GPG2_PRIVATE_KEY_FILENAME": "/bin/ps", "GPG2_PUBLIC_KEY_FILENAME": "/bin/ps"}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewSigningEngineFieldGroup(tt.config)
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
