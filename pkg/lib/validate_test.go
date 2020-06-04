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
		err    bool
	}{
		// Valid
		{name: "test1", config: "config1.yaml", schema: "quay-config-schema.json", want: true, err: false},

		// Invalid
		{name: "test2", config: "config2.yaml", schema: "quay-config-schema.json", want: false, err: false},

		// Error
		{name: "test3", config: "config3.yaml", schema: "quay-config-schema.json", want: false, err: true},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Get path of test data from name
		configPath := filepath.Join("testdata", tt.config)
		schemaPath := filepath.Join("testdata", tt.schema)

		t.Run(tt.name, func(t *testing.T) {
			result, err := ValidateSchema(configPath, schemaPath)

			// Got Error
			if err != nil {

				// Expected No Error
				if !tt.err {
					t.Errorf("Did not expect error: %s", err.Error())
					return
				}

				// Expected Error
				return
			}

			// Got Result
			if result.IsValid != tt.want {
				t.Errorf("Expected %v for %s. Received %v", tt.want, tt.config, result.IsValid)
			}
		})
	}

}
