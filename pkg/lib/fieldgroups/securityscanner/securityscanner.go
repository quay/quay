package securityscanner

import (
	"errors"

	"github.com/creasty/defaults"
)

// SecurityScannerFieldGroup represents the SecurityScannerFieldGroup config fields
type SecurityScannerFieldGroup struct {
	FeatureSecurityScanner              bool     `default:"false" validate:"" json:"FEATURE_SECURITY_SCANNER" yaml:"FEATURE_SECURITY_SCANNER"`
	SecurityScannerEndpoint             string   `default:"" validate:"" json:"SECURITY_SCANNER_ENDPOINT,omitempty" yaml:"SECURITY_SCANNER_ENDPOINT,omitempty"`
	SecurityScannerIndexingInterval     int      `default:"30" validate:"" json:"SECURITY_SCANNER_INDEXING_INTERVAL,omitempty" yaml:"SECURITY_SCANNER_INDEXING_INTERVAL,omitempty"`
	SecurityScannerNotifications        bool     `default:"false" validate:"" json:"FEATURE_SECURITY_NOTIFICATIONS" yaml:"FEATURE_SECURITY_NOTIFICATIONS"`
	SecurityScannerV4Endpoint           string   `default:"" validate:"" json:"SECURITY_SCANNER_V4_ENDPOINT,omitempty" yaml:"SECURITY_SCANNER_V4_ENDPOINT,omitempty"`
	SecurityScannerV4NamespaceWhitelist []string `default:"[]" validate:"" json:"SECURITY_SCANNER_V4_NAMESPACE_WHITELIST,omitempty" yaml:"SECURITY_SCANNER_V4_NAMESPACE_WHITELIST,omitempty"`
	SecurityScannerV4PSK                string   `default:"" json:"SECURITY_SCANNER_V4_PSK,omitempty" yaml:"SECURITY_SCANNER_V4_PSK,omitempty"`
}

// NewSecurityScannerFieldGroup creates a new SecurityScannerFieldGroup
func NewSecurityScannerFieldGroup(fullConfig map[string]interface{}) (*SecurityScannerFieldGroup, error) {
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
	if value, ok := fullConfig["SECURITY_SCANNER_V4_PSK"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerV4PSK, ok = value.(string)
		if !ok {
			return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_V4_PSK must be of type string")
		}
	}

	if value, ok := fullConfig["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"]; ok {

		// newSecurityScannerFieldGroup.SecurityScannerV4NamespaceWhitelist = value.([]string)
		for _, element := range value.([]interface{}) {
			strElement, ok := element.(string)
			if !ok {
				return newSecurityScannerFieldGroup, errors.New("SECURITY_SCANNER_V4_NAMESPACE_WHITELIST must be of type []string")
			}

			newSecurityScannerFieldGroup.SecurityScannerV4NamespaceWhitelist = append(
				newSecurityScannerFieldGroup.SecurityScannerV4NamespaceWhitelist,
				strElement,
			)
		}
	}

	return newSecurityScannerFieldGroup, nil
}
