package lib

import (
	"path/filepath"
	"testing"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateSchema(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config string
		schema string
		want   bool
	}{
		{"test1", "config1.yaml", "quay-config-schema.json", true},
		{"test2", "config2.yaml", "quay-config-schema.json", false},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Get path of test data from name
		configPath := filepath.Join("testdata", tt.config)
		schemaPath := filepath.Join("testdata", tt.schema)

		t.Run(tt.name, func(t *testing.T) {
			result, _ := ValidateSchema(configPath, schemaPath)
			if result != tt.want {
				t.Error()
			}
		})
	}

}
