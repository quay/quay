package fieldgroups

// Validate checks the configuration settings for this field group
func (fg *ActionLogArchivingFieldGroup) Validate() []ValidationError {

	// Make empty errors
	errors := []ValidationError{}

	// If feature action log rotation is off, no need to validate
	if !fg.FeatureActionLogRotation {
		return errors
	}

	// If path is empty
	if fg.ActionLogArchivePath == "" {

		newError := ValidationError{
			Tags:    []string{"FEATURE_ACTION_LOG_ARCHIVING", "ACTION_LOG_ARCHIVE_PATH"},
			Policy:  "A Requires B",
			Message: "FEATURE_ACTION_LOG_ARCHIVING requires ACTION_LOG_ARCHIVE_PATH",
		}
		errors = append(errors, newError)

	}

	// If location is empty
	if fg.ActionLogArchiveLocation == "" {

		newError := ValidationError{
			Tags:    []string{"FEATURE_ACTION_LOG_ARCHIVING", "ACTION_LOG_ARCHIVE_LOCATION"},
			Policy:  "A Requires B",
			Message: "FEATURE_ACTION_LOG_ARCHIVING requires ACTION_LOG_ARCHIVE_LOCATION",
		}
		errors = append(errors, newError)
	}

	// If distributed storage config is missing
	if fg.DistributedStorageConfig == nil {
		newError := ValidationError{
			Tags:    []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Policy:  "A is Required",
			Message: "DISTRIBUTED_STORAGE_CONFIG is required",
		}
		errors = append(errors, newError)
		return errors

	}
	validLocation := false
	for location := range *fg.DistributedStorageConfig {
		if fg.ActionLogArchiveLocation == location {
			validLocation = true
			break
		}
	}
	if !validLocation {
		newError := ValidationError{
			Tags:    []string{"ACTION_LOG_ARCHIVE_LOCATION", "DISTRIBUTED_STORAGE_CONFIG"},
			Policy:  "A In DistributedStorageConfig",
			Message: "ACTION_LOG_ARCHIVE_LOCATION must be in DISTRIBUTED_STORAGE_CONFIG",
		}
		errors = append(errors, newError)
	}

	// Return errors
	return errors

}
