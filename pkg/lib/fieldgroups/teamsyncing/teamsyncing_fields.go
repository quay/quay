package teamsyncing

// Fields returns a list of strings representing the fields in this field group
func (fg *TeamSyncingFieldGroup) Fields() []string {
	return []string{"FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP", "FEATURE_TEAM_SYNCING", "TEAM_RESYNC_STALE_TIME"}
}
