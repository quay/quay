package fieldgroups

import (
	"errors"
	"github.com/creasty/defaults"
)

// GitHubBuildTriggerFieldGroup represents the GitHubBuildTriggerFieldGroup config fields
type GitHubBuildTriggerFieldGroup struct {
	FeatureBuildSupport bool                       `default:"" validate:""`
	FeatureGithubBuild  bool                       `default:"false" validate:""`
	GithubTriggerConfig *GithubTriggerConfigStruct `default:"" validate:""`
}

// GithubTriggerConfigStruct represents the GithubTriggerConfigStruct config fields
type GithubTriggerConfigStruct struct {
	OrgRestrict          bool          `default:"false" validate:""`
	ApiEndpoint          string        `default:"" validate:""`
	ClientSecret         string        `default:"" validate:""`
	GithubEndpoint       string        `default:"" validate:""`
	ClientId             string        `default:"" validate:""`
	AllowedOrganizations []interface{} `default:"[]" validate:""`
}

// NewGitHubBuildTriggerFieldGroup creates a new GitHubBuildTriggerFieldGroup
func NewGitHubBuildTriggerFieldGroup(fullConfig map[string]interface{}) (FieldGroup, error) {
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
		value := fixInterface(value.(map[interface{}]interface{}))
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
	if value, ok := fullConfig["ALLOWED_ORGANIZATIONS"]; ok {
		newGithubTriggerConfigStruct.AllowedOrganizations, ok = value.([]interface{})
		if !ok {
			return newGithubTriggerConfigStruct, errors.New("ALLOWED_ORGANIZATIONS must be of type []interface{}")
		}
	}

	return newGithubTriggerConfigStruct, nil
}
