package fieldgroups

import (
	"testing"
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
		{name: "dbURIEmpty", config: map[string]interface{}{"DB_URI": "mysql://sql9351936:kBCXc7eizT@sql9.freesqldatabase.com:3306/sql9351936"}, want: "valid"},
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
				for _, err := range validationErrors {
					t.Errorf(err.Message)
				}
			}

		})
	}

}
