package githublogin

import (
	"testing"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateGitHubLoginTrigger(t *testing.T) {

	// Valid config

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "FeatureGithubBuildOff", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true}, want: "invalid"},
		{name: "Valid", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_ID":       "fc0ef3cf19f90de48af9",
			"CLIENT_SECRET":   "8bd923a5768a59f2e5f848752fa71ae62f4991ce",
			"GITHUB_ENDPOINT": "https://endpoint.com",
		}}, want: "valid"},
		{name: "NoClientSecret", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_ID":       "clientid",
			"GITHUB_ENDPOINT": "https://endpoint.com",
		}}, want: "invalid"},
		{name: "NoClientID", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_SECRET":   "clientsecret",
			"GITHUB_ENDPOINT": "https://endpoint.com",
		}}, want: "invalid"},
		{name: "NoGitHubEndpoint", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_ID":     "clientid",
			"CLIENT_SECRET": "clientsecret",
		}}, want: "invalid"},
		{name: "InvalidGitHubEndpoint", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_ID":       "clientid",
			"CLIENT_SECRET":   "clientsecret",
			"GITHUB_ENDPOINT": "not_a_valid_endpoint",
		}}, want: "invalid"},
		{name: "NoneInOrgList", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_ID":       "clientid",
			"CLIENT_SECRET":   "clientsecret",
			"GITHUB_ENDPOINT": "https://endpoint.com",
			"ORG_RESTRICT":    true,
		}}, want: "invalid"},
		{name: "ValidWithOrgList", config: map[string]interface{}{"FEATURE_GITHUB_LOGIN": true, "GITHUB_LOGIN_CONFIG": map[interface{}]interface{}{
			"CLIENT_ID":             "fc0ef3cf19f90de48af9",
			"CLIENT_SECRET":         "8bd923a5768a59f2e5f848752fa71ae62f4991ce",
			"GITHUB_ENDPOINT":       "https://endpoint.com",
			"ORG_RESTRICT":          true,
			"ALLOWED_ORGANIZATIONS": []interface{}{"Org1", "Org2"},
		}}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewGitHubLoginFieldGroup(tt.config)
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
