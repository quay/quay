package distributedstorage

import (
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *DistributedStorageFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "DistributedStorage"

	// Make empty errors
	errors := []shared.ValidationError{}

	if ok, err := shared.ValidateRequiredObject(fg.DistributedStorageConfig, "DISTRIBUTED_STORAGE_CONFIG", "DistributedStorage"); !ok {
		errors = append(errors, err)
		return errors
	}

	// If no storage locations
	if len(fg.DistributedStorageConfig) == 0 {
		newError := shared.ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    "DISTRIBUTED_STORAGE_CONFIG must contain at least one storage location.",
		}
		errors = append(errors, newError)
		return errors
	}

	for _, storageConf := range fg.DistributedStorageConfig {

		if storageConf.Name == "LocalStorage" && fg.FeatureStorageReplication {
			newError := shared.ValidationError{
				Tags:       []string{"FEATURE_STORAGE_REPLICATION"},
				FieldGroup: fgName,
				Message:    "FEATURE_STORAGE_REPLICATION is not supported by LocalStorage.",
			}
			errors = append(errors, newError)
		}

		// Do not validate local storage (fix me?)
		if storageConf.Name == "LocalStorage" {
			continue
		}

		if ok, err := shared.ValidateMinioStorage(opts, storageConf.Args, "DistributedStorage"); !ok {
			errors = append(errors, err)
		}
	}

	// Return errors
	return errors

}
