package fieldgroups

import "github.com/go-playground/validator/v10"

// FieldGroup is an interface that implements the Validate() function
type FieldGroup interface {
	Validate() validator.ValidationErrors
}

// Config is a struct that represents a configuration as a mapping of field groups
type Config map[string]FieldGroup

// NewConfig creates a Config struct from a map[string]interface{}
func NewConfig(fullConfig map[string]interface{}) Config {

	newConfig := Config{}
	newConfig["HostSettings"] = NewHostSettingsFieldGroup(fullConfig)
	newConfig["TagExpiration"] = NewTagExpirationFieldGroup(fullConfig)
	newConfig["UserVisibleSettings"] = NewUserVisibleSettingsFieldGroup(fullConfig)

	return newConfig
}
