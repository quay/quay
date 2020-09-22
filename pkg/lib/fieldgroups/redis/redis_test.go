package redis

import (
	"fmt"
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateRedis tests the Validate function
func TestValidateRedis(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "NotSpecified", config: map[string]interface{}{}, want: "invalid"},
		{name: "Works", config: map[string]interface{}{"BUILDLOGS_REDIS": map[string]interface{}{"host": "redis", "port": 6379}, "USER_EVENTS_REDIS": map[string]interface{}{"host": "redis", "port": 6379}}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewRedisFieldGroup(tt.config)
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
				fmt.Println(validationErrors[0].Message)
			}

		})
	}
}
