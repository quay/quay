package apptokenauthentication

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *AppTokenAuthenticationFieldGroup) Validate() []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// If authentication type is disabled
	if fg.AuthenticationType != "AppToken" {
		return errors
	}

	// Ensure app tokens are enabled
	if !fg.FeatureAppSpecificTokens {
		newError := shared.ValidationError{
			Tags:    []string{"FEATURE_APP_SPECIFIC_TOKENS"},
			Policy:  "A is True",
			Message: "FEATURE_APP_SPECIFIC_TOKENS must be enabled if AUTHENTICATION_TYPE is AppToken",
		}
		errors = append(errors, newError)
	}

	// Ensure direct login is disabled
	if fg.FeatureDirectLogin {
		newError := shared.ValidationError{
			Tags:    []string{"FEATURE_DIRECT_LOGIN"},
			Policy:  "A is False",
			Message: "FEATURE_DIRECT_LOGIN must be disabled if AUTHENTICATION_TYPE is AppToken",
		}
		errors = append(errors, newError)
	}

	return errors

}
