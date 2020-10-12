package jwtauthentication

import (
	"errors"

	"github.com/creasty/defaults"
)

// JWTAuthenticationFieldGroup represents the JWTAuthenticationFieldGroup config fields
type JWTAuthenticationFieldGroup struct {
	AuthenticationType string `default:"Database" validate:"" json:"AUTHENTICATION_TYPE,omitempty" yaml:"AUTHENTICATION_TYPE,omitempty"`
	FeatureMailing     bool   `default:"true" validate:"" json:"FEATURE_MAILING,omitempty" yaml:"FEATURE_MAILING,omitempty"`
	JwtAuthIssuer      string `default:"" validate:"" json:"JWT_AUTH_ISSUER,omitempty" yaml:"JWT_AUTH_ISSUER,omitempty"`
	JwtGetuserEndpoint string `default:"" validate:"" json:"JWT_GETUSER_ENDPOINT,omitempty" yaml:"JWT_GETUSER_ENDPOINT,omitempty"`
	JwtQueryEndpoint   string `default:"" validate:"" json:"JWT_QUERY_ENDPOINT,omitempty" yaml:"JWT_QUERY_ENDPOINT,omitempty"`
	JwtVerifyEndpoint  string `default:"" validate:"" json:"JWT_VERIFY_ENDPOINT,omitempty" yaml:"JWT_VERIFY_ENDPOINT,omitempty"`
}

// NewJWTAuthenticationFieldGroup creates a new JWTAuthenticationFieldGroup
func NewJWTAuthenticationFieldGroup(fullConfig map[string]interface{}) (*JWTAuthenticationFieldGroup, error) {
	newJWTAuthenticationFieldGroup := &JWTAuthenticationFieldGroup{}
	defaults.Set(newJWTAuthenticationFieldGroup)

	if value, ok := fullConfig["AUTHENTICATION_TYPE"]; ok {
		newJWTAuthenticationFieldGroup.AuthenticationType, ok = value.(string)
		if !ok {
			return newJWTAuthenticationFieldGroup, errors.New("AUTHENTICATION_TYPE must be of type string")
		}
	}
	if value, ok := fullConfig["FEATURE_MAILING"]; ok {
		newJWTAuthenticationFieldGroup.FeatureMailing, ok = value.(bool)
		if !ok {
			return newJWTAuthenticationFieldGroup, errors.New("FEATURE_MAILING must be of type bool")
		}
	}
	if value, ok := fullConfig["JWT_AUTH_ISSUER"]; ok {
		newJWTAuthenticationFieldGroup.JwtAuthIssuer, ok = value.(string)
		if !ok {
			return newJWTAuthenticationFieldGroup, errors.New("JWT_AUTH_ISSUER must be of type string")
		}
	}
	if value, ok := fullConfig["JWT_GETUSER_ENDPOINT"]; ok {
		newJWTAuthenticationFieldGroup.JwtGetuserEndpoint, ok = value.(string)
		if !ok {
			return newJWTAuthenticationFieldGroup, errors.New("JWT_GETUSER_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["JWT_QUERY_ENDPOINT"]; ok {
		newJWTAuthenticationFieldGroup.JwtQueryEndpoint, ok = value.(string)
		if !ok {
			return newJWTAuthenticationFieldGroup, errors.New("JWT_QUERY_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["JWT_VERIFY_ENDPOINT"]; ok {
		newJWTAuthenticationFieldGroup.JwtVerifyEndpoint, ok = value.(string)
		if !ok {
			return newJWTAuthenticationFieldGroup, errors.New("JWT_VERIFY_ENDPOINT must be of type string")
		}
	}

	return newJWTAuthenticationFieldGroup, nil
}
