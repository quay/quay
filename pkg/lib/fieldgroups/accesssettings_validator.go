package fieldgroups

// Validate checks the configuration settings for this field group
func (fg *AccessSettingsFieldGroup) Validate() []ValidationError {

	// Make empty errors
	errors := []ValidationError{}

	// If feature direct login is off, others must be on
	if !fg.FeatureDirectLogin && !fg.FeatureGithubLogin && !fg.FeatureGoogleLogin {

		newError := ValidationError{
			Tags:    []string{"FEATURE_DIRECT_LOGIN", "FEATURE_GITHUB_LOGIN", "FEATURE_GOOGLE_LOGIN"},
			Policy:  "At Least One Of",
			Message: "At least one of (FEATURE_DIRECT_LOGIN, FEATURE_GITHUB_LOGIN, FEATURE_GOOGLE_LOGIN) must be enabled",
		}
		errors = append(errors, newError)
	}

	// Invite only user creation requires user creaiton
	if !fg.FeatureUserCreation && fg.FeatureInviteOnlyUserCreation {

		newError := ValidationError{
			Tags:    []string{"INVITE_USER_ONLY_CREATION", "FEATURE_USER_CREATION"},
			Policy:  "A Requires B",
			Message: "INVITE_USER_ONLY_CREATION requires FEATURE_USER_CREATION to be enabled",
		}
		errors = append(errors, newError)
	}

	// Return errors
	return errors
}
