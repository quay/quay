package distributedstorage

import (
	"fmt"
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
	"gopkg.in/yaml.v3"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateDistributedStorage(t *testing.T) {

	var config = []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - access_key: X
    bucket_name: quay-datastore
    hostname: jonathan-registry.com
    is_secure: true
    port: 443
    secret_key: X
    storage_path: /datastorage/registry`)

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "MissingStorageConfig", config: map[string]interface{}{}, want: "invalid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Load config into struct
			var conf map[string]interface{}
			if err := yaml.Unmarshal(config, &conf); err != nil {
				fmt.Println(err.Error())
			}

			// Get validation result
			fg, err := NewDistributedStorageFieldGroup(conf)
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
