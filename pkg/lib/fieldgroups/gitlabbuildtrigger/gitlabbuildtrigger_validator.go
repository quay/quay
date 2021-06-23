package gitlabbuildtrigger

import (
	"strings"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *GitLabBuildTriggerFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "GitLabBuildTrigger"

	// Make empty errors
	errors := []shared.ValidationError{}

	// If build support is off, return false
	if fg.FeatureBuildSupport == false {
		return errors
	}

	// If github trigger is off
	if fg.FeatureGitlabBuild == false {
		return errors
	}

	// Check for config
	if fg.GitlabTriggerConfig == nil {
		newError := shared.ValidationError{
			Tags:       []string{"GITLAB_TRIGGER_CONFIG"},
			FieldGroup: fgName,
			Message:    "GITLAB_TRIGGER_CONFIG is required for GitLabBuildTrigger",
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for endpoint
	if fg.GitlabTriggerConfig.GitlabEndpoint == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GITLAB_TRIGGER_CONFIG.GITLAB_ENDPOINT"},
			FieldGroup: fgName,
			Message:    "GITLAB_TRIGGER_CONFIG.GITLAB_ENDPOINT is required for GitLabBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if !strings.HasPrefix(fg.GitlabTriggerConfig.GitlabEndpoint, "http://") && !strings.HasPrefix(fg.GitlabTriggerConfig.GitlabEndpoint, "https://") {
		newError := shared.ValidationError{
			Tags:       []string{"GITLAB_TRIGGER_CONFIG.GITLAB_ENDPOINT"},
			FieldGroup: fgName,
			Message:    "GITLAB_TRIGGER_CONFIG.GITLAB_ENDPOINT must be a url",
		}
		errors = append(errors, newError)
	}

	// Check for client id
	if fg.GitlabTriggerConfig.ClientId == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GITLAB_TRIGGER_CONFIG.CLIENT_ID"},
			FieldGroup: fgName,
			Message:    "GITLAB_TRIGGER_CONFIG.CLIENT_ID is required for GitLabBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if fg.GitlabTriggerConfig.ClientSecret == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GITLAB_TRIGGER_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "GITLAB_TRIGGER_CONFIG.CLIENT_SECRET is required for GitLabBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check OAuth endpoint
	success := shared.ValidateGitLabOAuth(fg.GitlabTriggerConfig.ClientId, fg.GitlabTriggerConfig.ClientSecret)
	if !success {
		newError := shared.ValidationError{
			Tags:       []string{"GITLAB_TRIGGER_CONFIG.CLIENT_ID", "GITLAB_TRIGGER_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "Could not verify GitLab OAuth credentials",
		}
		errors = append(errors, newError)
	}

	return errors
}
