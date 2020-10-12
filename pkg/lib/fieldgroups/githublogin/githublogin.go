package githublogin

import (
	"errors"

	"github.com/creasty/defaults"
)

// GitHubLoginFieldGroup represents the GitHubLoginFieldGroup config fields
type GitHubLoginFieldGroup struct {
	FeatureGithubLogin bool                     `default:"false" validate:"" json:"FEATURE_GITHUB_LOGIN,omitempty" yaml:"FEATURE_GITHUB_LOGIN,omitempty"`
	GithubLoginConfig  *GithubLoginConfigStruct `default:"" validate:"" json:"GITHUB_LOGIN_CONFIG,omitempty" yaml:"GITHUB_LOGIN_CONFIG,omitempty"`
}

// GithubLoginConfigStruct represents the GithubLoginConfigStruct config fields
type GithubLoginConfigStruct struct {
	AllowedOrganizations []interface{} `default:"[]" validate:"" json:"ALLOWED_ORGANIZATIONS,omitempty" yaml:"ALLOWED_ORGANIZATIONS,omitempty"`
	OrgRestrict          bool          `default:"false" validate:"" json:"ORG_RESTRICT,omitempty" yaml:"ORG_RESTRICT,omitempty"`
	ApiEndpoint          string        `default:"" validate:"" json:"API_ENDPOINT,omitempty" yaml:"API_ENDPOINT,omitempty"`
	GithubEndpoint       string        `default:"" validate:"" json:"GITHUB_ENDPOINT,omitempty" yaml:"GITHUB_ENDPOINT,omitempty"`
	ClientId             string        `default:"" validate:"" json:"CLIENT_ID,omitempty" yaml:"CLIENT_ID,omitempty"`
	ClientSecret         string        `default:"" validate:"" json:"CLIENT_SECRET,omitempty" yaml:"CLIENT_SECRET,omitempty"`
}

// NewGitHubLoginFieldGroup creates a new GitHubLoginFieldGroup
func NewGitHubLoginFieldGroup(fullConfig map[string]interface{}) (*GitHubLoginFieldGroup, error) {
	newGitHubLoginFieldGroup := &GitHubLoginFieldGroup{}
	defaults.Set(newGitHubLoginFieldGroup)

	if value, ok := fullConfig["FEATURE_GITHUB_LOGIN"]; ok {
		newGitHubLoginFieldGroup.FeatureGithubLogin, ok = value.(bool)
		if !ok {
			return newGitHubLoginFieldGroup, errors.New("FEATURE_GITHUB_LOGIN must be of type bool")
		}
	}
	if value, ok := fullConfig["GITHUB_LOGIN_CONFIG"]; ok {
		var err error
		value := value.(map[string]interface{})
		newGitHubLoginFieldGroup.GithubLoginConfig, err = NewGithubLoginConfigStruct(value)
		if err != nil {
			return newGitHubLoginFieldGroup, err
		}
	}

	return newGitHubLoginFieldGroup, nil
}

// NewGithubLoginConfigStruct creates a new GithubLoginConfigStruct
func NewGithubLoginConfigStruct(fullConfig map[string]interface{}) (*GithubLoginConfigStruct, error) {
	newGithubLoginConfigStruct := &GithubLoginConfigStruct{}
	defaults.Set(newGithubLoginConfigStruct)

	if value, ok := fullConfig["ALLOWED_ORGANIZATIONS"]; ok {
		newGithubLoginConfigStruct.AllowedOrganizations, ok = value.([]interface{})
		if !ok {
			return newGithubLoginConfigStruct, errors.New("ALLOWED_ORGANIZATIONS must be of type []interface{}")
		}
	}
	if value, ok := fullConfig["ORG_RESTRICT"]; ok {
		newGithubLoginConfigStruct.OrgRestrict, ok = value.(bool)
		if !ok {
			return newGithubLoginConfigStruct, errors.New("ORG_RESTRICT must be of type bool")
		}
	}
	if value, ok := fullConfig["API_ENDPOINT"]; ok {
		newGithubLoginConfigStruct.ApiEndpoint, ok = value.(string)
		if !ok {
			return newGithubLoginConfigStruct, errors.New("API_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["GITHUB_ENDPOINT"]; ok {
		newGithubLoginConfigStruct.GithubEndpoint, ok = value.(string)
		if !ok {
			return newGithubLoginConfigStruct, errors.New("GITHUB_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_ID"]; ok {
		newGithubLoginConfigStruct.ClientId, ok = value.(string)
		if !ok {
			return newGithubLoginConfigStruct, errors.New("CLIENT_ID must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_SECRET"]; ok {
		newGithubLoginConfigStruct.ClientSecret, ok = value.(string)
		if !ok {
			return newGithubLoginConfigStruct, errors.New("CLIENT_SECRET must be of type string")
		}
	}

	return newGithubLoginConfigStruct, nil
}
