package githubbuildtrigger

import (
	"cuelang.org/go/pkg/strings"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *GitHubBuildTriggerFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "GitHubBuildTrigger"

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
			Tags:       []string{"GITHUB_TRIGGER_CONFIG"},
			FieldGroup: fgName,
			Message:    "GITHUB_TRIGGER_CONFIG is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for endpoint
	if fg.GithubTriggerConfig.GithubEndpoint == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT"},
			FieldGroup: fgName,
			Message:    "GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if !strings.HasPrefix(fg.GithubTriggerConfig.GithubEndpoint, "http://") && !strings.HasPrefix(fg.GithubTriggerConfig.GithubEndpoint, "https://") {
		newError := shared.ValidationError{
			Tags:       []string{"GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT"},
			FieldGroup: fgName,
			Message:    "GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT must be a url",
		}
		errors = append(errors, newError)
	}

	// Check for client id
	if fg.GithubTriggerConfig.ClientId == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GITHUB_TRIGGER_CONFIG.CLIENT_ID"},
			FieldGroup: fgName,
			Message:    "GITHUB_TRIGGER_CONFIG.CLIENT_ID is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if fg.GithubTriggerConfig.ClientSecret == "" {
		newError := shared.ValidationError{
			Tags:       []string{"GITHUB_TRIGGER_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "GITHUB_TRIGGER_CONFIG.CLIENT_SECRET is required for GitHubBuildTrigger",
		}
		errors = append(errors, newError)
	}

	// If restricted orgs, make sure
	if fg.GithubTriggerConfig.OrgRestrict == true && len(fg.GithubTriggerConfig.AllowedOrganizations) == 0 {
		newError := shared.ValidationError{
			Tags:       []string{"GITHUB_TRIGGER_CONFIG.ORG_RESTRICT", "GITHUB_TRIGGER_CONFIG.ALLOWED_ORGANIZATIONS"},
			FieldGroup: fgName,
			Message:    "GITHUB_TRIGGER_CONFIG.ALLOWED_ORGANIZATIONS must contain values if GITHUB_TRIGGER_CONFIG.ORG_RESTRICT is true",
		}
		errors = append(errors, newError)
	}

	// Check OAuth endpoint
	var success bool
	if opts.Mode != "testing" {
		success = shared.ValidateGitHubOAuth(fg.GithubTriggerConfig.ClientId, fg.GithubTriggerConfig.ClientSecret)
	} else {
		success = (fg.GithubTriggerConfig.ClientId == "test_client_key") && (fg.GithubTriggerConfig.ClientSecret == "test_secret_key")
	}

	if !success {
		newError := shared.ValidationError{
			Tags:       []string{"GITHUB_TRIGGER_CONFIG.CLIENT_ID", "GITHUB_TRIGGER_CONFIG.CLIENT_SECRET"},
			FieldGroup: fgName,
			Message:    "Could not verify GitHub OAuth credentials",
		}
		errors = append(errors, newError)
	}

	return errors

}
