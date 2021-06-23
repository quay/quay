package bitbucketbuildtrigger

import (
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *BitbucketBuildTriggerFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "BitbucketBuildTrigger"

	// Make empty errors
	errors := []shared.ValidationError{}

	// If build suppport is off, dont validate
	if !fg.FeatureBuildSupport {
		return errors
	}

	// If bitbucket build support is off, dont validate
	if !fg.FeatureBitbucketBuild {
		return errors
	}

	// Make sure config is set up correctly
	if fg.BitbucketTriggerConfig == nil {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG"},
			FieldGroup: fgName,
			Message:    "BITBUCKET_TRIGGER_CONFIG is required",
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for consumer key
	if fg.BitbucketTriggerConfig.ConsumerKey == "" {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG.CONSUMER_KEY"},
			FieldGroup: fgName,
			Message:    "BITBUCKET_TRIGGER_CONFIG.CONSUMER_KEY is required",
		}
		errors = append(errors, newError)
	}

	// Check consumer secret
	if fg.BitbucketTriggerConfig.ConsumerSecret == "" {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG.CONSUMER_SECRET"},
			FieldGroup: fgName,
			Message:    "BITBUCKET_TRIGGER_CONFIG.CONSUMER_SECRET is required",
		}
		errors = append(errors, newError)
	}

	// Check OAuth credentials
	if !shared.ValidateBitbucketOAuth(fg.BitbucketTriggerConfig.ConsumerKey, fg.BitbucketTriggerConfig.ConsumerSecret) {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG.CONSUMER_ID", "BITBUCKET_TRIGGER_CONFIG.CONSUMER_SECRET"},
			FieldGroup: fgName,
			Message:    "Cannot validate BITBUCKET_TRIGGER_CONFIG credentials",
		}
		errors = append(errors, newError)
	}

	// Return errors
	return errors

}
