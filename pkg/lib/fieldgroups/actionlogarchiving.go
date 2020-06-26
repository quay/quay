package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// ActionLogArchivingFieldGroup represents the ActionLogArchivingFieldGroup config fields
type ActionLogArchivingFieldGroup struct {
	FeatureActionLogRotation bool                            `default:"false" validate:""`
	ActionLogArchivePath     string                          `default:"" validate:"required_with=FeatureActionLogRotation"`
	ActionLogArchiveLocation string                          `default:"" validate:"required_with=FeatureActionLogRotation,omitempty,customValidateFoundInStorage"`
	DistributedStorageConfig *DistributedStorageConfigStruct `default:"" validate:""`
}

// DistributedStorageConfigStruct represents the DistributedStorageConfig struct
type DistributedStorageConfigStruct map[string]interface{}

// NewActionLogArchivingFieldGroup creates a new ActionLogArchivingFieldGroup
func NewActionLogArchivingFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newActionLogArchivingFieldGroup := &ActionLogArchivingFieldGroup{}
	defaults.Set(newActionLogArchivingFieldGroup)

	if value, ok := fullConfig["FEATURE_ACTION_LOG_ROTATION"]; ok {
		newActionLogArchivingFieldGroup.FeatureActionLogRotation = value.(bool)
	}
	if value, ok := fullConfig["ACTION_LOG_ARCHIVE_PATH"]; ok {
		newActionLogArchivingFieldGroup.ActionLogArchivePath = value.(string)
	}
	if value, ok := fullConfig["ACTION_LOG_ARCHIVE_LOCATION"]; ok {
		newActionLogArchivingFieldGroup.ActionLogArchiveLocation = value.(string)
	}
	if value, ok := fullConfig["DISTRIBUTED_STORAGE_CONFIG"]; ok {
		value := fixInterface(value.(map[interface{}]interface{}))
		newActionLogArchivingFieldGroup.DistributedStorageConfig = NewDistributedStorageConfigStruct(value)
	}

	return newActionLogArchivingFieldGroup
}

// NewDistributedStorageConfigStruct creates a new DistributedStorageConfigStruct
func NewDistributedStorageConfigStruct(fullConfig map[string]interface{}) *DistributedStorageConfigStruct {
	newDistributedStorageConfigStruct := DistributedStorageConfigStruct{}
	for key, value := range fullConfig {
		newDistributedStorageConfigStruct[key] = value
	}
	return &newDistributedStorageConfigStruct
}

// Validate checks the configuration settings for this field group
func (fg *ActionLogArchivingFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()

	validate.RegisterValidation("customValidateFoundInStorage", customValidateFoundInStorage)

	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
