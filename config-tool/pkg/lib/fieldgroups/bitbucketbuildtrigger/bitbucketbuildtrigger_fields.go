package bitbucketbuildtrigger

// Fields returns a list of strings representing the fields in this field group
func (fg *BitbucketBuildTriggerFieldGroup) Fields() []string {
	return []string{"BITBUCKET_TRIGGER_CONFIG", "FEATURE_BITBUCKET_BUILD", "FEATURE_BUILD_SUPPORT"}
}
