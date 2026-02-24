package oidc

import (
	"errors"
	"fmt"
	"strings"

	"github.com/creasty/defaults"
)

// OIDC represents the OIDC config fields
type OIDCFieldGroup struct {
	OIDCProviders      []*OIDCProvider `default:"[]" validate:"" json:"-" yaml:"-"`
	ServerHostname     string          `default:"" validate:"" json:"SERVER_HOSTNAME,omitempty" yaml:"SERVER_HOSTNAME,omitempty"`
	PreferredUrlScheme string          `default:"https" validate:"" json:"PREFERRED_URL_SCHEME,omitempty" yaml:"PREFERRED_URL_SCHEME,omitempty"`
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

	if value, ok := fullConfig["SERVER_HOSTNAME"]; ok {
		if strVal, ok := value.(string); ok {
			newOIDCFieldGroup.ServerHostname = strVal
		}
	}
	if value, ok := fullConfig["PREFERRED_URL_SCHEME"]; ok {
		if strVal, ok := value.(string); ok {
			newOIDCFieldGroup.PreferredUrlScheme = strVal
		}
	}

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

// ServiceID derives the OIDC service ID from the provider's config prefix.
// This matches the Python logic in oauth/oidc.py: lowercase of everything
// before the first underscore (e.g., "AUTH0" → "auth0", "MY_CUSTOM" → "my").
func (p *OIDCProvider) ServiceID() string {
	idx := strings.Index(p._Prefix, "_")
	if idx >= 0 {
		return strings.ToLower(p._Prefix[:idx])
	}
	return strings.ToLower(p._Prefix)
}

// RedirectURL constructs the OAuth2 redirect URL for the given provider.
// Returns an empty string if ServerHostname is not configured.
func (fg *OIDCFieldGroup) RedirectURL(provider *OIDCProvider) string {
	if fg.ServerHostname == "" {
		return ""
	}
	scheme := fg.PreferredUrlScheme
	if scheme == "" {
		scheme = "https"
	}
	return fmt.Sprintf("%s://%s/oauth2/%s/callback", scheme, fg.ServerHostname, provider.ServiceID())
}
