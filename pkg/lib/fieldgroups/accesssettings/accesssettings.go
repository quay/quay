package accesssettings

import (
	"errors"

	"github.com/creasty/defaults"
)

// AccessSettingsFieldGroup represents the AccessSettingsFieldGroup config fields
type AccessSettingsFieldGroup struct {
	AuthenticationType             string `default:"Database" validate:""`
	FeatureAnonymousAccess         bool   `default:"true" validate:""`
	FeatureDirectLogin             bool   `default:"true" validate:""`
	FeatureGithubLogin             bool   `default:"false" validate:""`
	FeatureGoogleLogin             bool   `default:"false" validate:""`
	FeatureInviteOnlyUserCreation  bool   `default:"false" validate:""`
	FeaturePartialUserAutocomplete bool   `default:"true" validate:""`
	FeatureUsernameConfirmation    bool   `default:"true" validate:""`
	FeatureUserCreation            bool   `default:"true" validate:""`
	FeatureUserLastAccessed        bool   `default:"true" validate:""`
	FeatureUserLogAccess           bool   `default:"false" validate:""`
	FeatureUserMetadata            bool   `default:"false" validate:""`
	FeatureUserRename              bool   `default:"false" validate:""`
	FreshLoginTimeout              string `default:"10m" validate:""`
	UserRecoveryTokenLifetime      string `default:"30m" validate:""`
}

// NewAccessSettingsFieldGroup creates a new AccessSettingsFieldGroup
func NewAccessSettingsFieldGroup(fullConfig map[string]interface{}) (*AccessSettingsFieldGroup, error) {
	newAccessSettingsFieldGroup := &AccessSettingsFieldGroup{}
	defaults.Set(newAccessSettingsFieldGroup)

	if value, ok := fullConfig["AUTHENTICATION_TYPE"]; ok {
		newAccessSettingsFieldGroup.AuthenticationType, ok = value.(string)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("AUTHENTICATION_TYPE must be of type string")
		}
	}
	if value, ok := fullConfig["FEATURE_ANONYMOUS_ACCESS"]; ok {
		newAccessSettingsFieldGroup.FeatureAnonymousAccess, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_ANONYMOUS_ACCESS must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_DIRECT_LOGIN"]; ok {
		newAccessSettingsFieldGroup.FeatureDirectLogin, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_DIRECT_LOGIN must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_GITHUB_LOGIN"]; ok {
		newAccessSettingsFieldGroup.FeatureGithubLogin, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_GITHUB_LOGIN must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_GOOGLE_LOGIN"]; ok {
		newAccessSettingsFieldGroup.FeatureGoogleLogin, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_GOOGLE_LOGIN must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_INVITE_ONLY_USER_CREATION"]; ok {
		newAccessSettingsFieldGroup.FeatureInviteOnlyUserCreation, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_INVITE_ONLY_USER_CREATION must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_PARTIAL_USER_AUTOCOMPLETE"]; ok {
		newAccessSettingsFieldGroup.FeaturePartialUserAutocomplete, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_PARTIAL_USER_AUTOCOMPLETE must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_USERNAME_CONFIRMATION"]; ok {
		newAccessSettingsFieldGroup.FeatureUsernameConfirmation, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USERNAME_CONFIRMATION must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_USER_CREATION"]; ok {
		newAccessSettingsFieldGroup.FeatureUserCreation, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USER_CREATION must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_USER_LAST_ACCESSED"]; ok {
		newAccessSettingsFieldGroup.FeatureUserLastAccessed, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USER_LAST_ACCESSED must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_USER_LOG_ACCESS"]; ok {
		newAccessSettingsFieldGroup.FeatureUserLogAccess, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USER_LOG_ACCESS must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_USER_METADATA"]; ok {
		newAccessSettingsFieldGroup.FeatureUserMetadata, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USER_METADATA must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_USER_RENAME"]; ok {
		newAccessSettingsFieldGroup.FeatureUserRename, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USER_RENAME must be of type bool")
		}
	}
	if value, ok := fullConfig["FRESH_LOGIN_TIMEOUT"]; ok {
		newAccessSettingsFieldGroup.FreshLoginTimeout, ok = value.(string)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FRESH_LOGIN_TIMEOUT must be of type string")
		}
	}
	if value, ok := fullConfig["USER_RECOVERY_TOKEN_LIFETIME"]; ok {
		newAccessSettingsFieldGroup.UserRecoveryTokenLifetime, ok = value.(string)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("USER_RECOVERY_TOKEN_LIFETIME must be of type string")
		}
	}

	return newAccessSettingsFieldGroup, nil
}
