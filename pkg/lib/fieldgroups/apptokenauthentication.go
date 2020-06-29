package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// AppTokenAuthenticationFieldGroup represents the AppTokenAuthenticationFieldGroup config fields
type AppTokenAuthenticationFieldGroup struct {
	AuthenticationType       string `default:"Database" validate:"oneof=Database LDAP JTW Keystone OIDC AppToken,eq=AppToken"`
	FeatureAppSpecificTokens bool   `default:"true" validate:"required"`
	FeatureDirectLogin       bool   `default:"true" validate:"isdefault"`
}

// NewAppTokenAuthenticationFieldGroup creates a new AppTokenAuthenticationFieldGroup
func NewAppTokenAuthenticationFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newAppTokenAuthenticationFieldGroup := &AppTokenAuthenticationFieldGroup{}
	defaults.Set(newAppTokenAuthenticationFieldGroup)

	if value, ok := fullConfig["AUTHENTICATION_TYPE"]; ok {
		newAppTokenAuthenticationFieldGroup.AuthenticationType = value.(string)
	}
	if value, ok := fullConfig["FEATURE_APP_SPECIFIC_TOKENS"]; ok {
		newAppTokenAuthenticationFieldGroup.FeatureAppSpecificTokens = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_DIRECT_LOGIN"]; ok {
		newAppTokenAuthenticationFieldGroup.FeatureDirectLogin = value.(bool)
	}

	return newAppTokenAuthenticationFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *AppTokenAuthenticationFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()

	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
