package gitlabbuildtrigger

// Fields returns a list of strings representing the fields in this field group
func (fg *GitLabBuildTriggerFieldGroup) Fields() []string {
	return []string{"FEATURE_BUILD_SUPPORT", "FEATURE_GITLAB_BUILD", "GITLAB_TRIGGER_CONFIG"}
}
