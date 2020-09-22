package gitlabbuildtrigger

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateGitLabBuildTrigger tests the Validate function
func TestValidateGitLabBuildTrigger(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "FeatureBuildOff", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": false}, want: "valid"},
		{name: "FeatureGitlabBuildOff", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true}, want: "invalid"},
		{name: "Valid", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true, "GITLAB_TRIGGER_CONFIG": map[string]interface{}{
			"CLIENT_ID":       "304c96b0015a469f6cdc907a22acbc5692d8ac2958b19a19a2585811e0c1019f",
			"CLIENT_SECRET":   "45060b331c39c30bd532eb71c720739d177f1a22238da470eab6a5e19f26057a",
			"GITLAB_ENDPOINT": "https://endpoint.com",
		}}, want: "valid"},
		{name: "BadCredentials", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true, "GITLAB_TRIGGER_CONFIG": map[string]interface{}{
			"CLIENT_ID":       "bad_client_id",
			"CLIENT_SECRET":   "bad_cluent_secret",
			"GITLAB_ENDPOINT": "https://endpoint.com",
		}}, want: "invalid"},
		{name: "NoClientSecret", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true, "GITLAB_TRIGGER_CONFIG": map[string]interface{}{
			"CLIENT_ID":       "clientid",
			"GITHUB_ENDPOINT": "https://endpoint.com",
		}}, want: "invalid"},
		{name: "NoClientID", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true, "GITLAB_TRIGGER_CONFIG": map[string]interface{}{
			"CLIENT_SECRET":   "clientsecret",
			"GITHUB_ENDPOINT": "https://endpoint.com",
		}}, want: "invalid"},
		{name: "NoGitlabEndpoint", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true, "GITLAB_TRIGGER_CONFIG": map[string]interface{}{
			"CLIENT_ID":     "clientid",
			"CLIENT_SECRET": "clientsecret",
		}}, want: "invalid"},
		{name: "InvalidGitlabEndpoint", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_GITLAB_BUILD": true, "GITLAB_TRIGGER_CONFIG": map[string]interface{}{
			"CLIENT_ID":       "clientid",
			"CLIENT_SECRET":   "clientsecret",
			"GITLAB_ENDPOINT": "not_a_valid_endpoint",
		}}, want: "invalid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewGitLabBuildTriggerFieldGroup(tt.config)
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
