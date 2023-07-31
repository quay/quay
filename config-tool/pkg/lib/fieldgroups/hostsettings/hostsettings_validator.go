package hostsettings

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *HostSettingsFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// check that hostname is present
	if ok, err := shared.ValidateRequiredString(fg.ServerHostname, "SERVER_HOSTNAME", "HostSettings"); !ok {
		errors = append(errors, err)
	}

	// check that hostname is url
	if ok, err := shared.ValidateIsHostname(fg.ServerHostname, "SERVER_HOSTNAME", "HostSettings"); !ok {
		errors = append(errors, err)
	}

	// Check that url scheme is one of http or https
	if ok, err := shared.ValidateIsOneOfString(fg.PreferredUrlScheme, []string{"http", "https"}, "PREFERRED_URL_SCHEME", "HostSettings"); !ok {
		errors = append(errors, err)
	}

	// // If SSL is enabled
	if fg.PreferredUrlScheme == "https" && !fg.ExternalTlsTermination {

		// Validate certs are present
		if ok, err := shared.ValidateCertsPresent(opts, []string{"ssl.cert", "ssl.key"}, "HostSettings"); !ok {
			errors = append(errors, err)
			return errors
		}

		// Validate cert pair and hostname
		if ok, err := shared.ValidateCertPairWithHostname(opts.Certificates["ssl.cert"], opts.Certificates["ssl.key"], fg.ServerHostname, "HostSettigns"); !ok {
			errors = append(errors, err)
			return errors
		}

	}

	return errors
}
