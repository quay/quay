package accesssettings

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *AccessSettingsFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// Check that AuthType is one of
	if ok, err := shared.ValidateIsOneOfString(fg.AuthenticationType, []string{"Database", "LDAP", "JWT", "Keystone", "OIDC", "AppToken"}, "AUTHENTICATION_TYPE", "AccessSettings"); !ok {
		errors = append(errors, err)
	}

	// If feature direct login is off, others must be on
	if !fg.HasOIDCLogin {
		if ok, err := shared.ValidateAtLeastOneOfBool([]bool{fg.FeatureDirectLogin, fg.FeatureGithubLogin, fg.FeatureGoogleLogin}, []string{"FEATURE_DIRECT_LOGIN", "FEATURE_GITHUB_LOGIN", "FEATURE_GOOGLE_LOGIN"}, "AccessSettings"); !ok {
			errors = append(errors, err)
		}
	}

	// Make sure patterns are enforced if fields are present
	if fg.FreshLoginTimeout != "" {
		if ok, err := shared.ValidateTimePattern(fg.FreshLoginTimeout, "FRESH_LOGIN_TIMEOUT", "AccessSettings"); !ok {
			errors = append(errors, err)
		}
	}

	if fg.UserRecoveryTokenLifetime != "" {
		if ok, err := shared.ValidateTimePattern(fg.UserRecoveryTokenLifetime, "USER_RECOVERY_TOKEN_LIFETIME", "AccessSettings"); !ok {
			errors = append(errors, err)
		}
	}

	// Invite only user creation requires user creaiton
	if !fg.FeatureUserCreation && fg.FeatureInviteOnlyUserCreation {

		newError := shared.ValidationError{
			Tags:       []string{"INVITE_USER_ONLY_CREATION", "FEATURE_USER_CREATION"},
			FieldGroup: "AccessSettings",
			Message:    "INVITE_USER_ONLY_CREATION requires FEATURE_USER_CREATION to be enabled",
		}
		errors = append(errors, newError)
	}

	// Return errors
	return errors
}
