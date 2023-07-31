package githubbuildtrigger

// Fields returns a list of strings representing the fields in this field group
func (fg *GitHubBuildTriggerFieldGroup) Fields() []string {
	return []string{"FEATURE_BUILD_SUPPORT", "FEATURE_GITHUB_BUILD", "GITHUB_TRIGGER_CONFIG"}
}
