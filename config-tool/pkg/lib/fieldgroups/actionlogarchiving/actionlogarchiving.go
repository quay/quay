package actionlogarchiving

import (
	"errors"

	"github.com/creasty/defaults"
)

// ActionLogArchivingFieldGroup represents the ActionLogArchivingFieldGroup config fields
type ActionLogArchivingFieldGroup struct {
	ActionLogArchiveLocation string                          `default:"" validate:"" json:"ACTION_LOG_ARCHIVE_LOCATION,omitempty" yaml:"ACTION_LOG_ARCHIVE_LOCATION,omitempty"`
	ActionLogArchivePath     string                          `default:"" validate:"" json:"ACTION_LOG_ARCHIVE_PATH,omitempty" yaml:"ACTION_LOG_ARCHIVE_PATH,omitempty"`
	DistributedStorageConfig *DistributedStorageConfigStruct `default:"" validate:"" json:"DISTRIBUTED_STORAGE_CONFIG,omitempty" yaml:"DISTRIBUTED_STORAGE_CONFIG,omitempty"`
	FeatureActionLogRotation bool                            `default:"false" validate:"" json:"FEATURE_ACTION_LOG_ROTATION" yaml:"FEATURE_ACTION_LOG_ROTATION"`
}

// DistributedStorageConfigStruct represents the DistributedStorageConfig struct
type DistributedStorageConfigStruct map[string]interface{}

// NewActionLogArchivingFieldGroup creates a new ActionLogArchivingFieldGroup
func NewActionLogArchivingFieldGroup(fullConfig map[string]interface{}) (*ActionLogArchivingFieldGroup, error) {
	newActionLogArchivingFieldGroup := &ActionLogArchivingFieldGroup{}
	defaults.Set(newActionLogArchivingFieldGroup)

	if value, ok := fullConfig["ACTION_LOG_ARCHIVE_LOCATION"]; ok {
		newActionLogArchivingFieldGroup.ActionLogArchiveLocation, ok = value.(string)
		if !ok {
			return newActionLogArchivingFieldGroup, errors.New("ACTION_LOG_ARCHIVE_LOCATION must be of type string")
		}
	}
	if value, ok := fullConfig["ACTION_LOG_ARCHIVE_PATH"]; ok {
		newActionLogArchivingFieldGroup.ActionLogArchivePath, ok = value.(string)
		if !ok {
			return newActionLogArchivingFieldGroup, errors.New("ACTION_LOG_ARCHIVE_PATH must be of type string")
		}
	}
	if value, ok := fullConfig["DISTRIBUTED_STORAGE_CONFIG"]; ok {
		var err error
		value := value.(map[string]interface{})
		newActionLogArchivingFieldGroup.DistributedStorageConfig, err = NewDistributedStorageConfigStruct(value)
		if err != nil {
			return newActionLogArchivingFieldGroup, err
		}
	}
	if value, ok := fullConfig["FEATURE_ACTION_LOG_ROTATION"]; ok {
		newActionLogArchivingFieldGroup.FeatureActionLogRotation, ok = value.(bool)
		if !ok {
			return newActionLogArchivingFieldGroup, errors.New("FEATURE_ACTION_LOG_ROTATION must be of type bool")
		}
	}

	return newActionLogArchivingFieldGroup, nil
}

// NewDistributedStorageConfigStruct creates a new DistributedStorageConfigStruct
func NewDistributedStorageConfigStruct(fullConfig map[string]interface{}) (*DistributedStorageConfigStruct, error) {
	newDistributedStorageConfigStruct := DistributedStorageConfigStruct{}
	for key, value := range fullConfig {
		newDistributedStorageConfigStruct[key] = value
	}
	return &newDistributedStorageConfigStruct, nil
}
