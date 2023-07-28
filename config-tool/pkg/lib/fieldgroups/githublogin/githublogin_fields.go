package githublogin

// Fields returns a list of strings representing the fields in this field group
func (fg *GitHubLoginFieldGroup) Fields() []string {
	return []string{"FEATURE_GITHUB_LOGIN", "GITHUB_LOGIN_CONFIG"}
}
