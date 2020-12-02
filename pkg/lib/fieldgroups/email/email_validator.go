package email

import (
	net "net"
	"net/smtp"
	"strconv"
	"time"

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

	// Dial smtp server
	conn, err := net.DialTimeout("tcp", fg.MailServer+":"+strconv.Itoa(fg.MailPort), 3*time.Second)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"MAIL_SERVER"},
			FieldGroup: fgName,
			Message:    "Cannot reach " + fg.MailServer + ". Error: " + err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	client, err := smtp.NewClient(conn, fg.MailServer)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"MAIL_SERVER"},
			FieldGroup: fgName,
			Message:    "Cannot reach " + fg.MailServer + ". Error: " + err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	// If TLS is enabled.
	if fg.MailUseTls {
		config, err := shared.GetTlsConfig(opts)
		if err != nil {
			newError := shared.ValidationError{
				Tags:       []string{"MAIL_USE_TLS"},
				FieldGroup: fgName,
				Message:    err.Error(),
			}
			errors = append(errors, newError)
			return errors
		}
		config.ServerName = fg.MailServer

		err = client.StartTLS(config)
		if err != nil {
			newError := shared.ValidationError{
				Tags:       []string{"MAIL_USE_TLS"},
				FieldGroup: fgName,
				Message:    err.Error(),
			}
			errors = append(errors, newError)
			return errors
		}
	}

	// If auth is enabled, try to authenticate
	if fg.MailUseAuth {
		auth := smtp.PlainAuth("", fg.MailUsername, fg.MailPassword, fg.MailServer)
		if err = client.Auth(auth); err != nil {
			newError := shared.ValidationError{
				Tags:       []string{"MAIL_SERVER"},
				FieldGroup: fgName,
				Message:    "You must enable tls if you wish to use plain auth credentials. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return errors
		}
	}

	return errors
}
