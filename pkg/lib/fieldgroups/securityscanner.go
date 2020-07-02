package fieldgroups

import (
	"errors"
	"github.com/creasty/defaults"
)

// SecurityScannerFieldGroup represents the SecurityScannerFieldGroup config fields
type SecurityScannerFieldGroup struct {
	FeatureSecurityScanner              bool          `default:"false" validate:""`
	SecurityScannerEndpoint             string        `default:"" validate:""`
	SecurityScannerIndexingInterval     int           `default:"30" validate:""`
	SecurityScannerNotifications        bool          `default:"false" validate:""`
	SecurityScannerV4Endpoint           string        `default:"" validate:""`
	SecurityScannerV4NamespaceWhitelist []interface{} `default:"[]" validate:""`
}

// NewSecurityScannerFieldGroup creates a new SecurityScannerFieldGroup
func NewSecurityScannerFieldGroup(fullConfig map[string]interface{}) (FieldGroup, error) {
	newSecurityScannerFieldGroup := &SecurityScannerFieldGroup{}
	defaults.Set(newSecurityScannerFieldGroup)

	if value, ok := fullConfig["FEATURE_SECURITY_SCANNER"]; ok {
		newSecurityScannerFieldGroup.FeatureSecurityScanner, ok = value.(bool)
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("FEATURE_SECURITY_SCANNER must be of type bool")
		}
	}
	if value, ok := fullConfig["SECURITY_SCANNER_ENDPOINT"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerEndpoint, ok = value.(string)
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["SECURITY_SCANNER_INDEXING_INTERVAL"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerIndexingInterval, ok = value.(int)
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_INDEXING_INTERVAL must be of type int")
		}
	}
	if value, ok := fullConfig["SECURITY_SCANNER_NOTIFICATIONS"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerNotifications, ok = value.(bool)
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_NOTIFICATIONS must be of type bool")
		}
	}
	if value, ok := fullConfig["SECURITY_SCANNER_V4_ENDPOINT"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerV4Endpoint, ok = value.(string)
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_V4_ENDPOINT must be of type string")
		}
	}
	if value, ok := fullConfig["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerV4NamespaceWhitelist, ok = value.([]interface{})
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_V4_NAMESPACE_WHITELIST must be of type []interface{}")
		}
	}

	return newSecurityScannerFieldGroup, nil
}
