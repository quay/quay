package apptokenauthentication

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *AppTokenAuthenticationFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "AppTokenAuthentication"

	// Make empty errors
	errors := []shared.ValidationError{}

	// If authentication type is disabled
	if fg.AuthenticationType != "AppToken" {
		return errors
	}

	// Ensure app tokens are enabled
	if !fg.FeatureAppSpecificTokens {
		newError := shared.ValidationError{
			Tags:       []string{"FEATURE_APP_SPECIFIC_TOKENS"},
			FieldGroup: fgName,
			Message:    "FEATURE_APP_SPECIFIC_TOKENS must be enabled if AUTHENTICATION_TYPE is AppToken",
		}
		errors = append(errors, newError)
	}

	// Ensure direct login is disabled
	if fg.FeatureDirectLogin {
		newError := shared.ValidationError{
			Tags:       []string{"FEATURE_DIRECT_LOGIN"},
			FieldGroup: fgName,
			Message:    "FEATURE_DIRECT_LOGIN must be disabled if AUTHENTICATION_TYPE is AppToken",
		}
		errors = append(errors, newError)
	}

	return errors

}
