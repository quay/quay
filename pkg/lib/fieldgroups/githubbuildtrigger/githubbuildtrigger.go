package githubbuildtrigger

import (
	"errors"

	"github.com/creasty/defaults"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// GitHubBuildTriggerFieldGroup represents the GitHubBuildTriggerFieldGroup config fields
type GitHubBuildTriggerFieldGroup struct {
	FeatureBuildSupport bool                       `default:"" validate:"" yaml:"FEATURE_BUILD_SUPPORT"`
	FeatureGithubBuild  bool                       `default:"false" validate:"" yaml:"FEATURE_GITHUB_BUILD"`
	GithubTriggerConfig *GithubTriggerConfigStruct `default:"" validate:"" yaml:"GITHUB_TRIGGER_CONFIG"`
}

// GithubTriggerConfigStruct represents the GithubTriggerConfigStruct config fields
type GithubTriggerConfigStruct struct {
	AllowedOrganizations []interface{} `default:"[]" validate:"" yaml:"ALLOWED_ORGANIZATIONS"`
	OrgRestrict          bool          `default:"false" validate:"" yaml:"ORG_RESTRICT"`
	ApiEndpoint          string        `default:"" validate:"" yaml:"API_ENDPOINT"`
	ClientSecret         string        `default:"" validate:"" yaml:"CLIENT_SECRET"`
	GithubEndpoint       string        `default:"" validate:"" yaml:"GITHUB_ENDPOINT"`
	ClientId             string        `default:"" validate:"" yaml:"CLIENT_ID"`
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
		value := shared.FixInterface(value.(map[interface{}]interface{}))
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
