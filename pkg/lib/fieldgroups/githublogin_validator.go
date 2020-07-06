package fieldgroups

import (
	"cuelang.org/go/pkg/strings"
)

// Validate checks the configuration settings for this field group
func (fg *GitHubLoginFieldGroup) Validate() []ValidationError {

	// Make empty errors
	errors := []ValidationError{}

	// If github trigger is off
	if fg.FeatureGithubLogin == false {
		return errors
	}

	// Check for config
	if fg.GithubLoginConfig == nil {
		newError := ValidationError{
			Tags:    []string{"GITHUB_LOGIN_CONFIG"},
			Policy:  "A is Required",
			Message: "GITHUB_LOGIN_CONFIG is required for GitHubLogin",
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for endpoint
	if fg.GithubLoginConfig.GithubEndpoint == "" {
		newError := ValidationError{
			Tags:    []string{"GITHUB_LOGIN_CONFIG.GITHUB_ENDPOINT"},
			Policy:  "A is Required",
			Message: "GITHUB_LOGIN_CONFIG.GITHUB_ENDPOINT is required for GitHubLogin",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if !strings.HasPrefix(fg.GithubLoginConfig.GithubEndpoint, "http://") && !strings.HasPrefix(fg.GithubLoginConfig.GithubEndpoint, "https://") {
		newError := ValidationError{
			Tags:    []string{"GITHUB_LOGIN_CONFIG.GITHUB_ENDPOINT"},
			Policy:  "A is URL",
			Message: "GITHUB_LOGIN_CONFIG.GITHUB_ENDPOINT must be a url",
		}
		errors = append(errors, newError)
	}

	// Check for client id
	if fg.GithubLoginConfig.ClientId == "" {
		newError := ValidationError{
			Tags:    []string{"GITHUB_LOGIN_CONFIG.CLIENT_ID"},
			Policy:  "A is Required",
			Message: "GITHUB_LOGIN_CONFIG.CLIENT_ID is required for GitHubLogin",
		}
		errors = append(errors, newError)
	}

	// Check for endpoint
	if fg.GithubLoginConfig.ClientSecret == "" {
		newError := ValidationError{
			Tags:    []string{"GITHUB_LOGIN_CONFIG.CLIENT_SECRET"},
			Policy:  "A is Required",
			Message: "GITHUB_LOGIN_CONFIG.CLIENT_SECRET is required for GitHubLogin",
		}
		errors = append(errors, newError)
	}

	// If restricted orgs, make sure
	if fg.GithubLoginConfig.OrgRestrict == true && len(fg.GithubLoginConfig.AllowedOrganizations) == 0 {
		newError := ValidationError{
			Tags:    []string{"GITHUB_LOGIN_CONFIG.ORG_RESTRICT", "GITHUB_LOGIN_CONFIG.ALLOWED_ORGANIZATIONS"},
			Policy:  "A is Required",
			Message: "GITHUB_LOGIN_CONFIG.ALLOWED_ORGANIZATIONS must contain values if GITHUB_LOGIN_CONFIG.ORG_RESTRICT is true",
		}
		errors = append(errors, newError)
	}

	return errors

}
