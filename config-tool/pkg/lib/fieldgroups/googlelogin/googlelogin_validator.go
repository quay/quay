package googlelogin

import (
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *GoogleLoginFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "GoogleLogin"

	var errors []shared.ValidationError

	// If google login is off, return false
	if fg.FeatureGoogleLogin == false {
		return errors
	}

	// Check for config
	if fg.GoogleLoginConfig == nil {
		newError := shared.ValidationError{
			Tags:       []string{"GOOGLE_LOGIN_CONFIG"},
			FieldGroup: fgName,
			Message:    "GOOGLE_LOGIN_CONFIG is required for GoogleLogin",
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for client id
	if fg.GoogleLoginConfig.ClientId == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GOOGLE_LOGIN_CONFIG.CLIENT_ID"},
			FieldGroup: fgName,
			Message:    "GOOGLE_LOGIN_CONFIG.CLIENT_ID is required for GoogleLogin",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if fg.GoogleLoginConfig.ClientSecret == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GOOGLE_LOGIN_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "GOOGLE_LOGIN_CONFIG.CLIENT_SECRET is required for GoogleLogin",
		}
		errors = append(errors, newError)
	}

	// Check OAuth endpoint
	success := shared.ValidateGoogleOAuth(fg.GoogleLoginConfig.ClientId, fg.GoogleLoginConfig.ClientSecret)
	if !success {
		newError := shared.ValidationError{
			Tags:       []string{"GOOGLE_LOGIN_CONFIG.CLIENT_ID", "GOOGLE_LOGIN_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "Could not verify Google OAuth credentials",
		}
		errors = append(errors, newError)
	}

	return errors
}
