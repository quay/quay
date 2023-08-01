package securityscanner

// Fields returns a list of strings representing the fields in this field group
func (fg *SecurityScannerFieldGroup) Fields() []string {
	return []string{"FEATURE_SECURITY_SCANNER", "SECURITY_SCANNER_ENDPOINT", "SECURITY_SCANNER_INDEXING_INTERVAL", "SECURITY_SCANNER_NOTIFICATIONS", "SECURITY_SCANNER_V4_ENDPOINT", "SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"}
}
