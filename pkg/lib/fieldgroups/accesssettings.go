package fieldgroups

import (
	"errors"
	"github.com/creasty/defaults"
)

// AccessSettingsFieldGroup represents the AccessSettingsFieldGroup config fields
type AccessSettingsFieldGroup struct {
	FeatureDirectLogin            bool `default:"true" validate:""`
	FeatureGithubLogin            bool `default:"false" validate:""`
	FeatureGoogleLogin            bool `default:"false" validate:""`
	FeatureInviteOnlyUserCreation bool `default:"false" validate:""`
	FeatureUserCreation           bool `default:"true" validate:""`
}

// NewAccessSettingsFieldGroup creates a new AccessSettingsFieldGroup
func NewAccessSettingsFieldGroup(fullConfig map[string]interface{}) (FieldGroup, error) {
	newAccessSettingsFieldGroup := &AccessSettingsFieldGroup{}
	defaults.Set(newAccessSettingsFieldGroup)

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
	if value, ok := fullConfig["FEATURE_USER_CREATION"]; ok {
		newAccessSettingsFieldGroup.FeatureUserCreation, ok = value.(bool)
		if !ok {
			return newAccessSettingsFieldGroup, errors.New("FEATURE_USER_CREATION must be of type bool")
		}
	}

	return newAccessSettingsFieldGroup, nil
}
