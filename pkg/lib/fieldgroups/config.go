package fieldgroups

import (
	"fmt"
	"github.com/go-playground/validator/v10"
)

// FieldGroup is an interface that implements the Validate() function
type FieldGroup interface {
	Validate() validator.ValidationErrors
}

// Config is a struct that represents a configuration as a mapping of field groups
type Config map[string]FieldGroup

// NewConfig creates a Config struct from a map[string]interface{}
func NewConfig(fullConfig map[string]interface{}) Config {

	newConfig := Config{}
	newConfig["ActionLogArchiving"] = NewActionLogArchivingFieldGroup(fullConfig)
	newConfig["UserVisibleSettings"] = NewUserVisibleSettingsFieldGroup(fullConfig)
	newConfig["AccessSettings"] = NewAccessSettingsFieldGroup(fullConfig)
	newConfig["Documentation"] = NewDocumentationFieldGroup(fullConfig)
	newConfig["TeamSyncing"] = NewTeamSyncingFieldGroup(fullConfig)

	return newConfig
}

// fixInterface converts a map[interface{}]interface{} into a map[string]interface{}
func fixInterface(input map[interface{}]interface{}) map[string]interface{} {
	output := make(map[string]interface{})
	for key, value := range input {
		strKey := fmt.Sprintf("%v", key)
		output[strKey] = value
	}
	return output
}
