package distributedstorage

// Fields returns a list of strings representing the fields in this field group
func (fg *DistributedStorageFieldGroup) Fields() []string {
	return []string{"DISTRIBUTED_STORAGE_CONFIG", "DISTRIBUTED_STORAGE_PREFERENCE", "DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS", "FEATURE_STORAGE_REPLICATION"}
}
