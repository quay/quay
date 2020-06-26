package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// SecurityScannerFieldGroup represents the SecurityScannerFieldGroup config fields
type SecurityScannerFieldGroup struct {
	SecurityScannerEndpoint             string        `default:"" validate:"required_with=FeatureSecurityScanner|,omitempty,url,customGetHost"`
	SecurityScannerV4Endpoint           string        `default:"" validate:"required_with=FeatureSecurityScanner,omitempty,url,customGetHost"`
	SecurityScannerIndexingInterval     int           `default:"30" validate:""`
	FeatureSecurityScanner              bool          `default:"false" validate:""`
	SecurityScannerNotifications        bool          `default:"false" validate:""`
	SecurityScannerV4NamespaceWhitelist []interface{} `default:"[]" validate:""`
}

// NewSecurityScannerFieldGroup creates a new SecurityScannerFieldGroup
func NewSecurityScannerFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newSecurityScannerFieldGroup := &SecurityScannerFieldGroup{}
	defaults.Set(newSecurityScannerFieldGroup)

	if value, ok := fullConfig["SECURITY_SCANNER_ENDPOINT"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerEndpoint = value.(string)
	}
	if value, ok := fullConfig["SECURITY_SCANNER_V4_ENDPOINT"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerV4Endpoint = value.(string)
	}
	if value, ok := fullConfig["SECURITY_SCANNER_INDEXING_INTERVAL"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerIndexingInterval = value.(int)
	}
	if value, ok := fullConfig["FEATURE_SECURITY_SCANNER"]; ok {
		newSecurityScannerFieldGroup.FeatureSecurityScanner = value.(bool)
	}
	if value, ok := fullConfig["SECURITY_SCANNER_NOTIFICATIONS"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerNotifications = value.(bool)
	}
	if value, ok := fullConfig["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerV4NamespaceWhitelist = value.([]interface{})
	}

	return newSecurityScannerFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *SecurityScannerFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()

	validate.RegisterValidation("customGetHost", customGetHost)
	validate.RegisterValidation("customGetHost", customGetHost)

	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
