package gitlabbuildtrigger

import (
	"errors"

	"github.com/creasty/defaults"
)

// GitLabBuildTriggerFieldGroup represents the GitLabBuildTriggerFieldGroup config fields
type GitLabBuildTriggerFieldGroup struct {
	FeatureBuildSupport bool                       `default:"" validate:"" json:"FEATURE_BUILD_SUPPORT,omitempty" yaml:"FEATURE_BUILD_SUPPORT,omitempty"`
	FeatureGitlabBuild  bool                       `default:"false" validate:"" json:"FEATURE_GITLAB_BUILD,omitempty" yaml:"FEATURE_GITLAB_BUILD,omitempty"`
	GitlabTriggerConfig *GitlabTriggerConfigStruct `default:"" validate:"" json:"GITLAB_TRIGGER_CONFIG,omitempty" yaml:"GITLAB_TRIGGER_CONFIG,omitempty"`
}

// GitlabTriggerConfigStruct represents the GitlabTriggerConfigStruct config fields
type GitlabTriggerConfigStruct struct {
	GitlabEndpoint string `default:"" validate:"" json:"GITLAB_ENDPOINT,omitempty" yaml:"GITLAB_ENDPOINT,omitempty"`
	ClientId       string `default:"" validate:"" json:"CLIENT_ID,omitempty" yaml:"CLIENT_ID,omitempty"`
	ClientSecret   string `default:"" validate:"" json:"CLIENT_SECRET,omitempty" yaml:"CLIENT_SECRET,omitempty"`
}

// NewGitLabBuildTriggerFieldGroup creates a new GitLabBuildTriggerFieldGroup
func NewGitLabBuildTriggerFieldGroup(fullConfig map[string]interface{}) (*GitLabBuildTriggerFieldGroup, error) {
	newGitLabBuildTriggerFieldGroup := &GitLabBuildTriggerFieldGroup{}
	defaults.Set(newGitLabBuildTriggerFieldGroup)

	if value, ok := fullConfig["FEATURE_BUILD_SUPPORT"]; ok {
		newGitLabBuildTriggerFieldGroup.FeatureBuildSupport, ok = value.(bool)
		if !ok {
			return newGitLabBuildTriggerFieldGroup, errors.New("FEATURE_BUILD_SUPPORT must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_GITLAB_BUILD"]; ok {
		newGitLabBuildTriggerFieldGroup.FeatureGitlabBuild, ok = value.(bool)
		if !ok {
			return newGitLabBuildTriggerFieldGroup, errors.New("FEATURE_GITLAB_BUILD must be of type bool")
		}
	}
	if value, ok := fullConfig["GITLAB_TRIGGER_CONFIG"]; ok {
		var err error
		value := value.(map[string]interface{})
		newGitLabBuildTriggerFieldGroup.GitlabTriggerConfig, err = NewGitlabTriggerConfigStruct(value)
		if err != nil {
			return newGitLabBuildTriggerFieldGroup, err
		}
	}

	return newGitLabBuildTriggerFieldGroup, nil
}

// NewGitlabTriggerConfigStruct creates a new GitlabTriggerConfigStruct
func NewGitlabTriggerConfigStruct(fullConfig map[string]interface{}) (*GitlabTriggerConfigStruct, error) {
	newGitlabTriggerConfigStruct := &GitlabTriggerConfigStruct{}
	defaults.Set(newGitlabTriggerConfigStruct)

	if value, ok := fullConfig["GITLAB_ENDPOINT"]; ok {
		newGitlabTriggerConfigStruct.GitlabEndpoint, ok = value.(string)
		if !ok {
			return newGitlabTriggerConfigStruct, errors.New("GITLAB_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_ID"]; ok {
		newGitlabTriggerConfigStruct.ClientId, ok = value.(string)
		if !ok {
			return newGitlabTriggerConfigStruct, errors.New("CLIENT_ID must be of type string")
		}
	}
	if value, ok := fullConfig["CLIENT_SECRET"]; ok {
		newGitlabTriggerConfigStruct.ClientSecret, ok = value.(string)
		if !ok {
			return newGitlabTriggerConfigStruct, errors.New("CLIENT_SECRET must be of type string")
		}
	}

	return newGitlabTriggerConfigStruct, nil
}
