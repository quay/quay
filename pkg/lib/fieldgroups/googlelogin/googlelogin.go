package googlelogin

import (
	"errors"

	"github.com/creasty/defaults"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// GoogleLoginFieldGroup represents the GoogleLoginFieldGroup config fields
type GoogleLoginFieldGroup struct {
	FeatureGoogleLogin bool                     `default:"false" validate:"" yaml:"FEATURE_GOOGLE_LOGIN"`
	GoogleLoginConfig  *GoogleLoginConfigStruct `default:"" validate:"" yaml:"GOOGLE_LOGIN_CONFIG"`
}

// GoogleLoginConfigStruct represents the GoogleLoginConfigStruct config fields
type GoogleLoginConfigStruct struct {
	ClientSecret string `default:"" validate:"" yaml:"CLIENT_SECRET"`
	ClientId     string `default:"" validate:"" yaml:"CLIENT_ID"`
}

// NewGoogleLoginFieldGroup creates a new GoogleLoginFieldGroup
func NewGoogleLoginFieldGroup(fullConfig map[string]interface{}) (*GoogleLoginFieldGroup, error) {
	newGoogleLoginFieldGroup := &GoogleLoginFieldGroup{}
	defaults.Set(newGoogleLoginFieldGroup)

	if value, ok := fullConfig["FEATURE_GOOGLE_LOGIN"]; ok {
		newGoogleLoginFieldGroup.FeatureGoogleLogin, ok = value.(bool)
		if !ok {
			return newGoogleLoginFieldGroup, errors.New("FEATURE_GOOGLE_LOGIN must be of type bool")
		}
	}
	if value, ok := fullConfig["GOOGLE_LOGIN_CONFIG"]; ok {
		var err error
		value := shared.FixInterface(value.(map[interface{}]interface{}))
		newGoogleLoginFieldGroup.GoogleLoginConfig, err = NewGoogleLoginConfigStruct(value)
		if err != nil {
			return newGoogleLoginFieldGroup, err
		}
	}

	return newGoogleLoginFieldGroup, nil
}

// NewGoogleLoginConfigStruct creates a new GoogleLoginConfigStruct
func NewGoogleLoginConfigStruct(fullConfig map[string]interface{}) (*GoogleLoginConfigStruct, error) {
	newGoogleLoginConfigStruct := &GoogleLoginConfigStruct{}
	defaults.Set(newGoogleLoginConfigStruct)

	if value, ok := fullConfig["CLIENT_SECRET"]; ok {
		newGoogleLoginConfigStruct.ClientSecret, ok = value.(string)
		if !ok {
			return newGoogleLoginConfigStruct, errors.New("CLIENT_SECRET must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_ID"]; ok {
		newGoogleLoginConfigStruct.ClientId, ok = value.(string)
		if !ok {
			return newGoogleLoginConfigStruct, errors.New("CLIENT_ID must be of type string")
		}
	}

	return newGoogleLoginConfigStruct, nil
}
