package distributedstorage

import (
	"fmt"
	"testing"

	"github.com/quay/quay/config-tool/pkg/lib/shared"
	"gopkg.in/yaml.v3"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateDistributedStorage(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config []byte
		want   string
	}{

		{name: "MissingStorageConfig", config: []byte(``), want: "invalid"},
		{name: "CorrectStorageConfig", config: []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - access_key: X
    bucket_name: quay-datastore
    hostname: jonathan-registry.com
    is_secure: true
    port: 443
    secret_key: X
    storage_path: /datastorage/registry`), want: "valid"},
		{name: "StorageWithRegionSet", config: []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - access_key: X
    bucket_name: quay-datastore
    hostname: jonathan-registry.com
    is_secure: true
    port: 443
    secret_key: X
    region_name: someregion
    storage_path: /datastorage/registry`), want: "valid"},
		{name: "StorageWithoutPortSet", config: []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - access_key: X
    bucket_name: quay-datastore
    hostname: jonathan-registry.com
    is_secure: true
    secret_key: X
    region_name: someregion
    storage_path: /datastorage/registry`), want: "valid"},
		{name: "StorageWithIPAddressSet", config: []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - access_key: X
    bucket_name: quay-datastore
    hostname: 1.2.3.4
    is_secure: true
    port: 443
    secret_key: X
    region_name: someregion
    storage_path: /datastorage/registry`), want: "valid"},
		{name: "StorageWithNoHostnameSet", config: []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - access_key: X
    bucket_name: quay-datastore
    is_secure: true
    port: 443
    secret_key: X
    region_name: someregion
    storage_path: /datastorage/registry`), want: "invalid"},
		{name: "StorageWithNoAccessParamsSet", config: []byte(`DISTRIBUTED_STORAGE_CONFIG:
  local_us:
  - RadosGWStorage
  - bucket_name: quay-datastore
    hostname: jonathan-registry.com
    region_name: someregion
    storage_path: /datastorage/registry`), want: "invalid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Load config into struct
			var conf map[string]interface{}
			if err := yaml.Unmarshal(tt.config, &conf); err != nil {
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
					t.Errorf("%s", err.Message)
				}
			}

		})
	}

}
