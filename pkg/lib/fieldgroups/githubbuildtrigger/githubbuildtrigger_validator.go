package githubbuildtrigger

import (
	"cuelang.org/go/pkg/strings"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *GitHubBuildTriggerFieldGroup) Validate() []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// If build support is off, return false
	if fg.FeatureBuildSupport == false {
		return errors
	}

	// If github trigger is off
	if fg.FeatureGithubBuild == false {
		return errors
	}

	// Check for config
	if fg.GithubTriggerConfig == nil {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG"},
			Policy:  "A is Required",
			Message: "GITHUB_TRIGGER_CONFIG is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for endpoint
	if fg.GithubTriggerConfig.GithubEndpoint == "" {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT"},
			Policy:  "A is Required",
			Message: "GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if !strings.HasPrefix(fg.GithubTriggerConfig.GithubEndpoint, "http://") && !strings.HasPrefix(fg.GithubTriggerConfig.GithubEndpoint, "https://") {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT"},
			Policy:  "A is URL",
			Message: "GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT must be a url",
		}
		errors = append(errors, newError)
	}

	// Check for client id
	if fg.GithubTriggerConfig.ClientId == "" {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG.CLIENT_ID"},
			Policy:  "A is Required",
			Message: "GITHUB_TRIGGER_CONFIG.CLIENT_ID is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if fg.GithubTriggerConfig.ClientSecret == "" {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG.CLIENT_SECRET"},
			Policy:  "A is Required",
			Message: "GITHUB_TRIGGER_CONFIG.CLIENT_SECRET is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// If restricted orgs, make sure
	if fg.GithubTriggerConfig.OrgRestrict == true && len(fg.GithubTriggerConfig.AllowedOrganizations) == 0 {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG.ORG_RESTRICT", "GITHUB_TRIGGER_CONFIG.ALLOWED_ORGANIZATIONS"},
			Policy:  "A is Required",
			Message: "GITHUB_TRIGGER_CONFIG.ALLOWED_ORGANIZATIONS must contain values if GITHUB_TRIGGER_CONFIG.ORG_RESTRICT is true",
		}
		errors = append(errors, newError)
	}

	// Check OAuth endpoint
	success := shared.ValidateGitHubOAuth(fg.GithubTriggerConfig.ClientId, fg.GithubTriggerConfig.ClientSecret)
	if !success {
		newError := shared.ValidationError{
			Tags:    []string{"GITHUB_TRIGGER_CONFIG.CLIENT_ID", "GITHUB_TRIGGER_CONFIG.CLIENT_SECRET"},
			Policy:  "A is Required",
			Message: "Could not verify GitHub OAuth credentials",
		}
		errors = append(errors, newError)
	}

	return errors

}
