package accesssettings

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateAccessSettings(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		// Valid
		{name: "checkFieldsNotPresent", config: map[string]interface{}{}, want: "valid"},
		{name: "checkNoLoginFeature", config: map[string]interface{}{"FEATURE_DIRECT_LOGIN": false}, want: "invalid"},
		{name: "checkBadAuthType", config: map[string]interface{}{"AUTHENTICATION_TYPE": "notarealauthtype"}, want: "invalid"},
		{name: "checkGithubLogin", config: map[string]interface{}{"FEATURE_DIRECT_LOGIN": false, "FEATURE_GITHUB_LOGIN": true}, want: "valid"},
		{name: "checkGoogleLogin", config: map[string]interface{}{"FEATURE_DIRECT_LOGIN": false, "FEATURE_GOOGLE_LOGIN": true}, want: "valid"},
		{name: "checkOIDC", config: map[string]interface{}{"FEATURE_DIRECT_LOGIN": false, "FEATURE_GOOGLE_LOGIN": false, "AUTH0_LOGIN_CONFIG": map[string]interface{}{}}, want: "valid"},
		{name: "checkInviteUser0", config: map[string]interface{}{"FEATURE_USER_CREATION": true, "FEATURE_INVITE_ONLY_USER_CREATION": false}, want: "valid"},
		{name: "checkInviteUser1", config: map[string]interface{}{"FEATURE_USER_CREATION": true, "FEATURE_INVITE_ONLY_USER_CREATION": true}, want: "valid"},
		{name: "checkInviteUser2", config: map[string]interface{}{"FEATURE_INVITE_ONLY_USER_CREATION": true}, want: "valid"},
		{name: "checkInviteUser3", config: map[string]interface{}{"FEATURE_USER_CREATION": false, "FEATURE_INVITE_ONLY_USER_CREATION": true}, want: "invalid"},
		{name: "checkInviteUser4", config: map[string]interface{}{"FEATURE_USER_CREATION": false, "FEATURE_INVITE_ONLY_USER_CREATION": false}, want: "valid"},
		{name: "checkIncorrectPattern", config: map[string]interface{}{"FEATURE_USER_CREATION": false, "FEATURE_INVITE_ONLY_USER_CREATION": false, "USER_RECOVERY_TOKEN_LIFETIME": "badpattern"}, want: "invalid"},
		{name: "checkCorrectPattern", config: map[string]interface{}{"FEATURE_USER_CREATION": false, "FEATURE_INVITE_ONLY_USER_CREATION": false, "USER_RECOVERY_TOKEN_LIFETIME": "1m"}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewAccessSettingsFieldGroup(tt.config)
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
