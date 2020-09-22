package googlelogin

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateGoogleLogin tests the Validate function
func TestValidateGoogleLogin(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "GoogleLoginNotSpecified", config: map[string]interface{}{}, want: "valid"},
		{name: "GoogleLoginOnMissingConfig", config: map[string]interface{}{"FEATURE_GOOGLE_LOGIN": true}, want: "invalid"},
		{name: "GoogleLoginMissingFields", config: map[string]interface{}{"FEATURE_GOOGLE_LOGIN": true, "GOOGLE_LOGIN_CONFIG": map[string]interface{}{}}, want: "invalid"},
		{name: "GoogleLoginBadCredentials", config: map[string]interface{}{"FEATURE_GOOGLE_LOGIN": true, "GOOGLE_LOGIN_CONFIG": map[string]interface{}{"CLIENT_ID": "bad_id", "CLIENT_SECRET": "bad_secret"}}, want: "invalid"},
		{name: "GoogleLoginGoodCredentials", config: map[string]interface{}{"FEATURE_GOOGLE_LOGIN": true, "GOOGLE_LOGIN_CONFIG": map[string]interface{}{"CLIENT_ID": "511815388398-ng379ngbt3ivpno3all76540eh11ebu7.apps.googleusercontent.com", "CLIENT_SECRET": "0mQogdczWFnNemnVp5esDuas"}}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewGoogleLoginFieldGroup(tt.config)
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
