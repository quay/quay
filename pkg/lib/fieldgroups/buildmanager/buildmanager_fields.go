package buildmanager

// Fields returns a list of strings representing the fields in this field group
func (fg *BuildManagerFieldGroup) Fields() []string {
	return []string{"FEATURE_BUILD_SUPPORT", "BUILD_MANAGER"}
}
