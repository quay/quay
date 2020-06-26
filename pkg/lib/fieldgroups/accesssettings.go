package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// AccessSettingsFieldGroup represents the AccessSettingsFieldGroup config fields
type AccessSettingsFieldGroup struct {
	FeatureGithubLogin            bool `default:"false" validate:"required_without_all=FeatureDirectLogin FeatureGoogleLogin"`
	FeatureDirectLogin            bool `default:"true" validate:"required_without_all=FeatureGithubLogin FeatureGoogleLogin"`
	FeatureInviteOnlyUserCreation bool `default:"false" validate:""`
	FeatureGoogleLogin            bool `default:"false" validate:"required_without_all=FeatureDirectLogin FeatureGithubLogin"`
	FeatureUserCreation           bool `default:"true" validate:"required_with=FeatureInviteOnlyUserCreation"`
}

// NewAccessSettingsFieldGroup creates a new AccessSettingsFieldGroup
func NewAccessSettingsFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newAccessSettingsFieldGroup := &AccessSettingsFieldGroup{}
	defaults.Set(newAccessSettingsFieldGroup)

	if value, ok := fullConfig["FEATURE_GITHUB_LOGIN"]; ok {
		newAccessSettingsFieldGroup.FeatureGithubLogin = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_DIRECT_LOGIN"]; ok {
		newAccessSettingsFieldGroup.FeatureDirectLogin = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_INVITE_ONLY_USER_CREATION"]; ok {
		newAccessSettingsFieldGroup.FeatureInviteOnlyUserCreation = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_GOOGLE_LOGIN"]; ok {
		newAccessSettingsFieldGroup.FeatureGoogleLogin = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_USER_CREATION"]; ok {
		newAccessSettingsFieldGroup.FeatureUserCreation = value.(bool)
	}

	return newAccessSettingsFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *AccessSettingsFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()

	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
