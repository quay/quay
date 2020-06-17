package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// HostSettingsFieldGroup represents the HostSettings config fields
type HostSettingsFieldGroup struct {
	ServerHostname         string `default:"" validate:"required"`
	PreferredURLScheme     string `default:"http" validate:"oneof=http https"`
	ExternalTLSTermination bool   `default:"false" validate:""`
}

// NewHostSettingsFieldGroup creates a new HostSettingsFieldGroup
func NewHostSettingsFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newHostSettings := &HostSettingsFieldGroup{}
	defaults.Set(newHostSettings)

	if value, ok := fullConfig["SERVER_HOSTNAME"]; ok {
		newHostSettings.ServerHostname = value.(string)
	}
	if value, ok := fullConfig["PREFERRED_URL_SCHEME"]; ok {
		newHostSettings.PreferredURLScheme = value.(string)
	}
	if value, ok := fullConfig["EXTERNAL_TLS_TERMINATION"]; ok {
		newHostSettings.ExternalTLSTermination = value.(bool)
	}

	return newHostSettings
}

// Validate checks the configuration settings for this field group
func (fg *HostSettingsFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()
	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
