package bitbucketbuildtrigger

import (
	"testing"
)

// TestValidateSchema tests the ValidateSchema function
func TestValidateBitbucketBuildTrigger(t *testing.T) {

	// Define test data
	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{

		{name: "BuildSupportOff", config: map[string]interface{}{}, want: "valid"},
		{name: "BuildSupportOnBitbucketOff", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true}, want: "valid"},
		{name: "BuildSupportOnBitbucketOnMissingFields", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true}, want: "invalid"},
		{name: "BuildSupportOnBitbucketOnMissingConsumerKey", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true, "BITBUCKET_TRIGGER_CONFIG": map[interface{}]interface{}{}}, want: "invalid"},
		{name: "BuildSupportOnBitbucketOnEmptyConsumerKey", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true, "BITBUCKET_TRIGGER_CONFIG": map[interface{}]interface{}{"CONSUMER_KEY": ""}}, want: "invalid"},
		{name: "BuildSupportOnBitbucketOnMissingConsumerSecret", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true, "BITBUCKET_TRIGGER_CONFIG": map[interface{}]interface{}{"CONSUMER_KEY": ""}}, want: "invalid"},
		{name: "BuildSupportOnBitbucketOnEmptyConsumerSecret", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true, "BITBUCKET_TRIGGER_CONFIG": map[interface{}]interface{}{"CONSUMER_KEY": "", "CONSUMER_SECRET": ""}}, want: "invalid"},
		{name: "BuildSupportOnBitbucketOnInvalidConfig", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true, "BITBUCKET_TRIGGER_CONFIG": map[interface{}]interface{}{"CONSUMER_KEY": "foo", "CONSUMER_SECRET": "bar"}}, want: "invalid"},
		{name: "BuildSupportOnBitbucketOnValidConfig", config: map[string]interface{}{"FEATURE_BUILD_SUPPORT": true, "FEATURE_BITBUCKET_BUILD": true, "BITBUCKET_TRIGGER_CONFIG": map[interface{}]interface{}{"CONSUMER_KEY": "A39bvHgf3ZJxdvAXyS", "CONSUMER_SECRET": "VtqYfxbjDNFUsYbsU3vcTTqbyGxbGvYf"}}, want: "valid"},
	}

	// Iterate through tests
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewBitbucketBuildTriggerFieldGroup(tt.config)
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
			}

		})
	}

}
