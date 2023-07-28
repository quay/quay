package email

import (
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *EmailFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "Email"

	// Make empty errors
	errors := []shared.ValidationError{}

	// Only validate if feature is on
	if fg.FeatureMailing == false {
		return errors
	}

	// Check for mail server
	if ok, err := shared.ValidateRequiredString(fg.MailServer, "MAIL_SERVER", fgName); !ok {
		errors = append(errors, err)
		return errors
	}

	// If FIPS is enabled, ensure mail tls is enabled
	if fg.FeatureFIPS && !fg.MailUseTls {
		newError := shared.ValidationError{
			Tags:       []string{"MAIL_USE_TLS", "FEATURE_FIPS"},
			FieldGroup: fgName,
			Message:    "MAIL_USE_TLS must be enabled when running in FIPS mode.",
		}
		errors = append(errors, newError)
		return errors
	}

	if ok, err := shared.ValidateEmailServer(opts, fg.MailServer, fg.MailPort, fg.MailUseTls, fg.MailUseAuth, fg.MailUsername, fg.MailPassword, fgName); !ok {
		errors = append(errors, err)
		return errors
	}

	return errors
}
