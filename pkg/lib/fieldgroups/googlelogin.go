package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// GoogleLoginFieldGroup represents the GoogleLoginFieldGroup config fields
type GoogleLoginFieldGroup struct {
	FeatureGoogleLogin string `default:"" validate:""`
	GoogleLoginConfig  *GoogleLoginConfigStruct
}

// GoogleLoginConfigStruct represents the GoogleLoginConfigStruct config fields
type GoogleLoginConfigStruct struct {
	ClientID     string `default:"" validate:""`
	ClientSecret string `default:"" validate:""`
}

// NewGoogleLoginFieldGroup creates a new GoogleLoginFieldGroup
func NewGoogleLoginFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newGoogleLoginFieldGroup := &GoogleLoginFieldGroup{}
	defaults.Set(newGoogleLoginFieldGroup)

	if value, ok := fullConfig["FEATURE_GOOGLE_LOGIN"]; ok {
		newGoogleLoginFieldGroup.FeatureGoogleLogin = value.(string)
	}
	if value, ok := fullConfig["GOOGLE_LOGIN_CONFIG"]; ok {
		value := fixInterface(value.(map[interface{}]interface{}))
		newGoogleLoginFieldGroup.GoogleLoginConfig = NewGoogleLoginConfigStruct(value)
	}

	return newGoogleLoginFieldGroup
}

// NewGoogleLoginConfigStruct creates a new GoogleLoginConfigStruct
func NewGoogleLoginConfigStruct(fullConfig map[string]interface{}) *GoogleLoginConfigStruct {
	newGoogleLoginConfigStruct := &GoogleLoginConfigStruct{}
	defaults.Set(newGoogleLoginConfigStruct)

	if value, ok := fullConfig["CLIENT_ID"]; ok {
		newGoogleLoginConfigStruct.ClientID = value.(string)
	}
	if value, ok := fullConfig["CLIENT_SECRET"]; ok {
		newGoogleLoginConfigStruct.ClientSecret = value.(string)
	}

	return newGoogleLoginConfigStruct
}

// Validate checks the configuration settings for this field group
func (fg *GoogleLoginFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()
	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
