package timemachine

// Fields returns a list of strings representing the fields in this field group
func (fg *TimeMachineFieldGroup) Fields() []string {
	return []string{"DEFAULT_TAG_EXPIRATION", "FEATURE_CHANGE_TAG_EXPIRATION", "TAG_EXPIRATION_OPTIONS"}
}
