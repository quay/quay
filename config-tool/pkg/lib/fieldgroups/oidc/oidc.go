package oidc

import (
	"errors"
	"strings"

	"github.com/creasty/defaults"
)

// OIDC represents the OIDC config fields
type OIDCFieldGroup struct {
	OIDCProviders []*OIDCProvider `default:"[]" validate:"" json:"-" yaml:"-"`
}

type OIDCProvider struct {
	_Prefix                    string        `default:"" validate:"" json:"-" yaml:"-"`
	OIDCServer                 string        `default:"" validate:"" json:"OIDC_SERVER,omitempty" yaml:"OIDC_SERVER,omitempty"`
	ClientID                   string        `default:"" validate:"" json:"CLIENT_ID,omitempty" yaml:"CLIENT_ID,omitempty"`
	ClientSecret               string        `default:"" validate:"" json:"CLIENT_SECRET,omitempty" yaml:"CLIENT_SECRET,omitempty"`
	ServiceIcon                string        `default:"" validate:"" json:"SERVICE_ICON,omitempty" yaml:"SERVICE_ICON,omitempty"`
	VerifiedEmailClaimName     string        `default:"" validate:"" json:"VERIFIED_EMAIL_CLAIM_NAME,omitempty" yaml:"VERIFIED_EMAIL_CLAIM_NAME,omitempty"`
	PreferredUsernameClaimName string        `default:"" validate:"" json:"PREFERRED_USERNAME_CLAIM_NAME,omitempty" yaml:"PREFERRED_USERNAME_CLAIM_NAME,omitempty"`
	LoginScopes                []interface{} `default:"" validate:"" json:"LOGIN_SCOPES,omitempty" yaml:"LOGIN_SCOPES,omitempty"`
	ServiceName                string        `default:"" validate:"" json:"SERVICE_NAME,omitempty" yaml:"SERVICE_NAME,omitempty"`
}

// NewOIDCFieldGroup creates a new OIDCFieldGroup
func NewOIDCFieldGroup(fullConfig map[string]interface{}) (*OIDCFieldGroup, error) {
	newOIDCFieldGroup := &OIDCFieldGroup{}
	defaults.Set(newOIDCFieldGroup)

	for key, value := range fullConfig {
		if providerConf, ok := value.(map[string]interface{}); ok {
			if strings.HasSuffix(key, "_LOGIN_CONFIG") && key != "GOOGLE_LOGIN_CONFIG" && key != "GITHUB_LOGIN_CONFIG" {
				prefix := strings.TrimSuffix(key, "_LOGIN_CONFIG")
				newProvider, err := NewOIDCProvider(prefix, providerConf)
				if err != nil {
					return nil, err
				}
				newOIDCFieldGroup.OIDCProviders = append(newOIDCFieldGroup.OIDCProviders, newProvider)
			}
		}
	}

	return newOIDCFieldGroup, nil
}

// NewOIDCProvider creates a new OIDCProvider
func NewOIDCProvider(prefix string, providerConfig map[string]interface{}) (*OIDCProvider, error) {
	newOIDCProvider := &OIDCProvider{}

	// Set dynamic prefix
	newOIDCProvider._Prefix = prefix

	if value, ok := providerConfig["OIDC_SERVER"]; ok {
		newOIDCProvider.OIDCServer, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("OIDC_SERVER must be of type string")
		}
	}
	if value, ok := providerConfig["CLIENT_ID"]; ok {
		newOIDCProvider.ClientID, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("CLIENT_ID must be of type string")
		}
	}
	if value, ok := providerConfig["CLIENT_SECRET"]; ok {
		newOIDCProvider.ClientSecret, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("CLIENT_SECRET must be of type bool")
		}
	}
	if value, ok := providerConfig["SERVICE_NAME"]; ok {
		newOIDCProvider.ServiceName, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("SERVICE_NAME must be of type string")
		}
	}
	if value, ok := providerConfig["SERVICE_ICON"]; ok {
		newOIDCProvider.ServiceIcon, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("SERVICE_ICON must be of type string")
		}
	}
	if value, ok := providerConfig["VERIFIED_EMAIL_CLAIM_NAME"]; ok {
		newOIDCProvider.VerifiedEmailClaimName, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("VERIFIED_EMAIL_CLAIM_NAME must be of type string")
		}
	}
	if value, ok := providerConfig["PREFERRED_USERNAME_CLAIM_NAME"]; ok {
		newOIDCProvider.PreferredUsernameClaimName, ok = value.(string)
		if !ok {
			return newOIDCProvider, errors.New("PREFERRED_USERNAME_CLAIM_NAME must be of type string")
		}
	}
	if value, ok := providerConfig["LOGIN_SCOPES"]; ok {
		newOIDCProvider.LoginScopes, ok = value.([]interface{})
		if !ok {
			return newOIDCProvider, errors.New("LOGIN_SCOPES must be of type string")
		}
	}

	return newOIDCProvider, nil
}
