package actionlogarchiving

// Fields returns a list of strings representing the fields in this field group
func (fg *ActionLogArchivingFieldGroup) Fields() []string {
	return []string{"ACTION_LOG_ARCHIVE_LOCATION", "ACTION_LOG_ARCHIVE_PATH", "DISTRIBUTED_STORAGE_CONFIG", "FEATURE_ACTION_LOG_ROTATION"}
}
