package actionlogarchiving

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateActionLogArchiving(t *testing.T) {

	distributedStorageConfig := map[string]interface{}{
		"validlocation": []interface{}{
			"LocalStorage",
			map[string]interface{}{
				"storage_path": "/some/path",
			},
		},
	}

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		// Valid
		{name: "checkMissingArchivePath", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true}, want: "invalid"},
		{name: "checkEmptyArchivePath", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true, "ACTION_LOG_ARCHIVE_PATH": ""}, want: "invalid"},
		{name: "checkArchivePathNoLocation", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true, "ACTION_LOG_ARCHIVE_PATH": "some/path"}, want: "invalid"},
		{name: "checkArchivePathEmptyLocation", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true, "ACTION_LOG_ARCHIVE_PATH": "some/path", "ACTION_LOG_ARCHIVE_LOCATION": "", "DISTRIBUTED_STORAGE_CONFIG": distributedStorageConfig}, want: "invalid"},
		{name: "checkArchivePathInValidLocation", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true, "ACTION_LOG_ARCHIVE_PATH": "some/path", "ACTION_LOG_ARCHIVE_LOCATION": "invalidlocation", "DISTRIBUTED_STORAGE_CONFIG": distributedStorageConfig}, want: "invalid"},
		{name: "checkArchivePathNoDistConfig", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true, "ACTION_LOG_ARCHIVE_PATH": "some/path", "ACTION_LOG_ARCHIVE_LOCATION": "invalidlocation"}, want: "invalid"},
		{name: "checkArchivePathValidLocation", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": true, "ACTION_LOG_ARCHIVE_PATH": "some/path", "ACTION_LOG_ARCHIVE_LOCATION": "validlocation", "DISTRIBUTED_STORAGE_CONFIG": distributedStorageConfig}, want: "valid"},
		{name: "checkArchivePathOff", config: map[string]interface{}{"FEATURE_ACTION_LOG_ROTATION": false}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewActionLogArchivingFieldGroup(tt.config)
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
