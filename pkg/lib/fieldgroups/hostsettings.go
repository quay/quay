package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// HostSettingsFieldGroupFieldGroup represents the HostSettingsFieldGroup config fields
type HostSettingsFieldGroup struct {
	ServerHostname         string `default:"" validate:"required"`
	PreferredURLScheme     string `default:"http" validate:"oneof=http https"`
	ExternalTLSTermination bool   `default:"false" validate:""`
}

// NewHostSettingsFieldGroup creates a new HostSettingsFieldGroup
func NewHostSettingsFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newHostSettingsFieldGroup := &HostSettingsFieldGroup{}
	defaults.Set(newHostSettingsFieldGroup)

	if value, ok := fullConfig["SERVER_HOSTNAME"]; ok {
		newHostSettingsFieldGroup.ServerHostname = value.(string)
	}
	if value, ok := fullConfig["PREFERRED_URL_SCHEME"]; ok {
		newHostSettingsFieldGroup.PreferredURLScheme = value.(string)
	}
	if value, ok := fullConfig["EXTERNAL_TLS_TERMINATION"]; ok {
		newHostSettingsFieldGroup.ExternalTLSTermination = value.(bool)
	}

	return newHostSettingsFieldGroup
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
