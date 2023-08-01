package teamsyncing

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateTeamSyncing tests the Validate function
func TestValidateTeamSyncing(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		{name: "Empty", config: map[string]interface{}{}, want: "valid"},
		{name: "BadSyncTime", config: map[string]interface{}{"TEAM_RESYNC_STALE_TIME": "10fff"}, want: "invalid"},
		{name: "GoodSyncTime", config: map[string]interface{}{"TEAM_RESYNC_STALE_TIME": "10m"}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewTeamSyncingFieldGroup(tt.config)
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
