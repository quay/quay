package elasticsearch

import (
	"testing"

	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// TestUseSslFieldParsing verifies that the UseSsl field is correctly parsed
// from config and defaults to true when omitted.
func TestUseSslFieldParsing(t *testing.T) {
	var tests = []struct {
		name       string
		config     map[string]interface{}
		wantUseSsl bool
	}{
		{
			name: "DefaultUseSsl",
			config: map[string]interface{}{
				"access_key": "key",
				"secret_key": "secret",
				"host":       "localhost",
				"port":       9200,
			},
			wantUseSsl: true,
		},
		{
			name: "ExplicitUseSslTrue",
			config: map[string]interface{}{
				"access_key": "key",
				"secret_key": "secret",
				"host":       "localhost",
				"port":       9200,
				"use_ssl":    true,
			},
			wantUseSsl: true,
		},
		{
			name: "ExplicitUseSslFalse",
			config: map[string]interface{}{
				"access_key": "key",
				"secret_key": "secret",
				"host":       "localhost",
				"port":       9200,
				"use_ssl":    false,
			},
			wantUseSsl: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			esConfig, err := NewElasticsearchConfigStruct(tt.config)
			if err != nil {
				t.Fatalf("Unexpected error: %s", err.Error())
			}
			if esConfig.UseSsl != tt.wantUseSsl {
				t.Errorf("Expected UseSsl=%v, got UseSsl=%v", tt.wantUseSsl, esConfig.UseSsl)
			}
		})
	}
}

// TestValidateSchema tests the ValidateSchema function
func TestValidateElasticSearch(t *testing.T) {

	// Valid config
	logsModelConfig := map[string]interface{}{
		"elasticsearch_config": map[string]interface{}{
			"access_key": "test_client_key",
			"secret_key": "test_secret_key",
			"host":       "bfd70499058e4485854f8bacf06af627.us-central1.gcp.cloud.es.io",
			"port":       9243,
		},
	}

	// Valid config with use_ssl explicitly true
	logsModelConfigSslTrue := map[string]interface{}{
		"elasticsearch_config": map[string]interface{}{
			"access_key": "test_client_key",
			"secret_key": "test_secret_key",
			"host":       "bfd70499058e4485854f8bacf06af627.us-central1.gcp.cloud.es.io",
			"port":       9243,
			"use_ssl":    true,
		},
	}

	// Valid config with use_ssl false
	logsModelConfigSslFalse := map[string]interface{}{
		"elasticsearch_config": map[string]interface{}{
			"access_key": "test_client_key",
			"secret_key": "test_secret_key",
			"host":       "bfd70499058e4485854f8bacf06af627.us-central1.gcp.cloud.es.io",
			"port":       9243,
			"use_ssl":    false,
		},
	}

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "Valid", config: map[string]interface{}{"LOGS_MODEL": "database"}, want: "valid"},
		{name: "MissingConfig", config: map[string]interface{}{"LOGS_MODEL": "elasticsearch"}, want: "invalid"},
		{name: "ValidConfig", config: map[string]interface{}{"LOGS_MODEL": "elasticsearch", "LOGS_MODEL_CONFIG": logsModelConfig}, want: "valid"},
		{name: "ValidConfigSslTrue", config: map[string]interface{}{"LOGS_MODEL": "elasticsearch", "LOGS_MODEL_CONFIG": logsModelConfigSslTrue}, want: "valid"},
		{name: "ValidConfigSslFalse", config: map[string]interface{}{"LOGS_MODEL": "elasticsearch", "LOGS_MODEL_CONFIG": logsModelConfigSslFalse}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewElasticSearchFieldGroup(tt.config)
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
