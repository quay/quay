package repomirror

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateRepoMirror tests the Validate function
func TestValidateRepoMirror(t *testing.T) {
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		{
			config: map[string]interface{}{"FEATURE_REPO_MIRROR": true, "REPO_MIRROR_SERVER_HOSTNAME": "google.com"},
			name:   "goodConfig",
			want:   "valid",
		},
		{
			config: map[string]interface{}{"FEATURE_REPO_MIRROR": true, "REPO_MIRROR_SERVER_HOSTNAME": "not a hostname"},
			name:   "badHostname",
			want:   "invalid",
		},
		{
			config: map[string]interface{}{"FEATURE_REPO_MIRROR": false, "REPO_MIRROR_SERVER_HOSTNAME": "not a hostname"},
			name:   "badHostnameFeatureOff",
			want:   "valid",
		},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewRepoMirrorFieldGroup(tt.config)
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
				for _, err := range validationErrors {
					t.Errorf(err.Message)
				}
			}

		})
	}
}
