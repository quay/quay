package githubbuildtrigger

import (
	"errors"

	"github.com/creasty/defaults"
)

// GitHubBuildTriggerFieldGroup represents the GitHubBuildTriggerFieldGroup config fields
type GitHubBuildTriggerFieldGroup struct {
	FeatureBuildSupport bool                       `default:"" validate:"" json:"FEATURE_BUILD_SUPPORT" yaml:"FEATURE_BUILD_SUPPORT"`
	FeatureGithubBuild  bool                       `default:"false" validate:"" json:"FEATURE_GITHUB_BUILD" yaml:"FEATURE_GITHUB_BUILD"`
	GithubTriggerConfig *GithubTriggerConfigStruct `default:"" validate:"" json:"GITHUB_TRIGGER_CONFIG" yaml:"GITHUB_TRIGGER_CONFIG"`
}

// GithubTriggerConfigStruct represents the GithubTriggerConfigStruct config fields
type GithubTriggerConfigStruct struct {
	AllowedOrganizations []interface{} `default:"[]" validate:"" json:"ALLOWED_ORGANIZATIONS" yaml:"ALLOWED_ORGANIZATIONS"`
	OrgRestrict          bool          `default:"false" validate:"" json:"ORG_RESTRICT" yaml:"ORG_RESTRICT"`
	ApiEndpoint          string        `default:"" validate:"" json:"API_ENDPOINT" yaml:"API_ENDPOINT"`
	ClientSecret         string        `default:"" validate:"" json:"CLIENT_SECRET" yaml:"CLIENT_SECRET"`
	GithubEndpoint       string        `default:"" validate:"" json:"GITHUB_ENDPOINT" yaml:"GITHUB_ENDPOINT"`
	ClientId             string        `default:"" validate:"" json:"CLIENT_ID" yaml:"CLIENT_ID"`
}

// NewGitHubBuildTriggerFieldGroup creates a new GitHubBuildTriggerFieldGroup
func NewGitHubBuildTriggerFieldGroup(fullConfig map[string]interface{}) (*GitHubBuildTriggerFieldGroup, error) {
	newGitHubBuildTriggerFieldGroup := &GitHubBuildTriggerFieldGroup{}
	defaults.Set(newGitHubBuildTriggerFieldGroup)

	if value, ok := fullConfig["FEATURE_BUILD_SUPPORT"]; ok {
		newGitHubBuildTriggerFieldGroup.FeatureBuildSupport, ok = value.(bool)
		if !ok {
			return newGitHubBuildTriggerFieldGroup, errors.New("FEATURE_BUILD_SUPPORT must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_GITHUB_BUILD"]; ok {
		newGitHubBuildTriggerFieldGroup.FeatureGithubBuild, ok = value.(bool)
		if !ok {
			return newGitHubBuildTriggerFieldGroup, errors.New("FEATURE_GITHUB_BUILD must be of type bool")
		}
	}
	if value, ok := fullConfig["GITHUB_TRIGGER_CONFIG"]; ok {
		var err error
		value := value.(map[string]interface{})
		newGitHubBuildTriggerFieldGroup.GithubTriggerConfig, err = NewGithubTriggerConfigStruct(value)
		if err != nil {
			return newGitHubBuildTriggerFieldGroup, err
		}
	}

	return newGitHubBuildTriggerFieldGroup, nil
}

// NewGithubTriggerConfigStruct creates a new GithubTriggerConfigStruct
func NewGithubTriggerConfigStruct(fullConfig map[string]interface{}) (*GithubTriggerConfigStruct, error) {
	newGithubTriggerConfigStruct := &GithubTriggerConfigStruct{}
	defaults.Set(newGithubTriggerConfigStruct)

	if value, ok := fullConfig["ALLOWED_ORGANIZATIONS"]; ok {
		newGithubTriggerConfigStruct.AllowedOrganizations, ok = value.([]interface{})
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("ALLOWED_ORGANIZATIONS must be of type []interface{}")
		}
	}
	if value, ok := fullConfig["ORG_RESTRICT"]; ok {
		newGithubTriggerConfigStruct.OrgRestrict, ok = value.(bool)
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("ORG_RESTRICT must be of type bool")
		}
	}
	if value, ok := fullConfig["API_ENDPOINT"]; ok {
		newGithubTriggerConfigStruct.ApiEndpoint, ok = value.(string)
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("API_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_SECRET"]; ok {
		newGithubTriggerConfigStruct.ClientSecret, ok = value.(string)
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("CLIENT_SECRET must be of type string")
		}
	}
	if value, ok := fullConfig["GITHUB_ENDPOINT"]; ok {
		newGithubTriggerConfigStruct.GithubEndpoint, ok = value.(string)
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("GITHUB_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_ID"]; ok {
		newGithubTriggerConfigStruct.ClientId, ok = value.(string)
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("CLIENT_ID must be of type string")
		}
	}

	return newGithubTriggerConfigStruct, nil
}
