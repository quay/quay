package hostsettings

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *HostSettingsFieldGroup) Validate() []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// check that hostname is present
	if ok, err := shared.ValidateRequiredString(fg.ServerHostname, "SERVER_HOSTNAME", "HostSettings"); !ok {
		errors = append(errors, err)
	}

	// check that hostname is url
	if ok, err := shared.ValidateIsURL(fg.ServerHostname, "SERVER_HOSTNAME", "HostSettings"); !ok {
		errors = append(errors, err)
	}

	// Check that url scheme is one of http or https
	if ok, err := shared.ValidateIsOneOfString(fg.PreferredUrlScheme, []string{"http", "https"}, "PREFERRED_URL_SCHEME", "HostSettings"); !ok {
		errors = append(errors, err)
	}

	// // If SSL is enabled
	// if fg.PreferredUrlScheme == "https" && !fg.ExternalTlsTermination {

	// 	shared.ValidateFileExists()
	// }

	return errors
}
