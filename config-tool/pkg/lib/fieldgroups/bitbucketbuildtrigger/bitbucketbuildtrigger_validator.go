package bitbucketbuildtrigger

import (
	"github.com/quay/quay/config-tool/pkg/lib/shared"
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

	// Check for client ID
	if fg.BitbucketTriggerConfig.ClientID == "" {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG.CLIENT_ID"},
			FieldGroup: fgName,
			Message:    "BITBUCKET_TRIGGER_CONFIG.CLIENT_ID is required",
		}
		errors = append(errors, newError)
	}

	// Check client secret
	if fg.BitbucketTriggerConfig.ClientSecret == "" {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "BITBUCKET_TRIGGER_CONFIG.CLIENT_SECRET is required",
		}
		errors = append(errors, newError)
	}

	// Check OAuth credentials
	if !shared.ValidateBitbucketOAuth(fg.BitbucketTriggerConfig.ClientID, fg.BitbucketTriggerConfig.ClientSecret) {
		newError := shared.ValidationError{
			Tags:       []string{"BITBUCKET_TRIGGER_CONFIG.CLIENT_ID", "BITBUCKET_TRIGGER_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "Cannot validate BITBUCKET_TRIGGER_CONFIG credentials",
		}
		errors = append(errors, newError)
	}

	// Return errors
	return errors

}
