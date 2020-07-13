package apptokenauthentication

import (
	"errors"
	"github.com/creasty/defaults"
)

// AppTokenAuthenticationFieldGroup represents the AppTokenAuthenticationFieldGroup config fields
type AppTokenAuthenticationFieldGroup struct {
	AuthenticationType       string `default:"Database" validate:"" yaml:"AUTHENTICATION_TYPE"`
	FeatureAppSpecificTokens bool   `default:"true" validate:"" yaml:"FEATURE_APP_SPECIFIC_TOKENS"`
	FeatureDirectLogin       bool   `default:"true" validate:"" yaml:"FEATURE_DIRECT_LOGIN"`
}

// NewAppTokenAuthenticationFieldGroup creates a new AppTokenAuthenticationFieldGroup
func NewAppTokenAuthenticationFieldGroup(fullConfig map[string]interface{}) (*AppTokenAuthenticationFieldGroup, error) {
	newAppTokenAuthenticationFieldGroup := &AppTokenAuthenticationFieldGroup{}
	defaults.Set(newAppTokenAuthenticationFieldGroup)

	if value, ok := fullConfig["AUTHENTICATION_TYPE"]; ok {
		newAppTokenAuthenticationFieldGroup.AuthenticationType, ok = value.(string)
		if !ok {
			return newAppTokenAuthenticationFieldGroup, errors.New("AUTHENTICATION_TYPE must be of type string")
		}
	}
	if value, ok := fullConfig["FEATURE_APP_SPECIFIC_TOKENS"]; ok {
		newAppTokenAuthenticationFieldGroup.FeatureAppSpecificTokens, ok = value.(bool)
		if !ok {
			return newAppTokenAuthenticationFieldGroup, errors.New("FEATURE_APP_SPECIFIC_TOKENS must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_DIRECT_LOGIN"]; ok {
		newAppTokenAuthenticationFieldGroup.FeatureDirectLogin, ok = value.(bool)
		if !ok {
			return newAppTokenAuthenticationFieldGroup, errors.New("FEATURE_DIRECT_LOGIN must be of type bool")
		}
	}

	return newAppTokenAuthenticationFieldGroup, nil
}
