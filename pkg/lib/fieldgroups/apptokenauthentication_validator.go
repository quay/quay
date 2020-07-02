package fieldgroups

// Validate checks the configuration settings for this field group
func (fg *AppTokenAuthenticationFieldGroup) Validate() []ValidationError {

	// Make empty errors
	errors := []ValidationError{}

	// If authentication type is disabled
	if fg.AuthenticationType != "AppToken" {
		return errors
	}

	// Ensure app tokens are enabled
	if !fg.FeatureAppSpecificTokens {
		newError := ValidationError{
			Tags:    []string{"FEATURE_APP_SPECIFIC_TOKENS"},
			Policy:  "A is True",
			Message: "FEATURE_APP_SPECIFIC_TOKENS must be enabled if AUTHENTICATION_TYPE is AppToken",
		}
		errors = append(errors, newError)
	}

	// Ensure direct login is disabled
	if fg.FeatureDirectLogin {
		newError := ValidationError{
			Tags:    []string{"FEATURE_DIRECT_LOGIN"},
			Policy:  "A is False",
			Message: "FEATURE_DIRECT_LOGIN must be disabled if AUTHENTICATION_TYPE is AppToken",
		}
		errors = append(errors, newError)
	}

	return errors

}
