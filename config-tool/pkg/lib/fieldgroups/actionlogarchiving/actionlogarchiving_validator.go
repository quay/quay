package actionlogarchiving

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *ActionLogArchivingFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// If feature action log rotation is off, no need to validate
	if !fg.FeatureActionLogRotation {
		return errors
	}

	// Check path is present
	if ok, err := shared.ValidateRequiredString(fg.ActionLogArchivePath, "ACTION_LOG_ARCHIVE_PATH", "ActionLogArchiving"); !ok {
		errors = append(errors, err)
	}

	// Check location is present
	if ok, err := shared.ValidateRequiredString(fg.ActionLogArchiveLocation, "ACTION_LOG_ARCHIVE_LOCATION", "ActionLogArchiving"); !ok {
		errors = append(errors, err)
	}

	// Check config is present
	if ok, err := shared.ValidateRequiredObject(fg.DistributedStorageConfig, "DISTRIBUTED_STORAGE_CONFIG", "ActionLogArchiving"); !ok {
		errors = append(errors, err)
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
		newError := shared.ValidationError{
			Tags:       []string{"ACTION_LOG_ARCHIVE_LOCATION", "DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: "ActionLogArchiving",
			Message:    "ACTION_LOG_ARCHIVE_LOCATION must be in DISTRIBUTED_STORAGE_CONFIG",
		}
		errors = append(errors, newError)
	}

	// Return errors
	return errors

}
