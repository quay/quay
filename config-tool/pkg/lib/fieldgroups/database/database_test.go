package database

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateDatabase(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "dbURIMissing", config: map[string]interface{}{}, want: "invalid"},
		{name: "dbURIMissing", config: map[string]interface{}{"DB_URI": ""}, want: "invalid"},
		{name: "dbURIInvalid", config: map[string]interface{}{"DB_URI": "not a url"}, want: "invalid"},
		{name: "dbURIPostgres", config: map[string]interface{}{"DB_URI": "postgresql://user:password@postgres:5432/quay"}, want: "invalid"},

		// Quay currently requires the pymysql library to be specified in the DB_URI
		{name: "ValidMysqlURI", config: map[string]interface{}{"DB_URI": "mysql+pymysql://root:password@mysql:3306/quay"}, want: "valid"},
		{name: "MissingPyMysql", config: map[string]interface{}{"DB_URI": "mysql://root:password@mysql:3306/quay"}, want: "invalid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewDatabaseFieldGroup(tt.config)
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
