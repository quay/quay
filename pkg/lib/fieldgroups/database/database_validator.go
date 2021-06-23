package database

import (
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *DatabaseFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "Database"

	// Make empty errors
	errors := []shared.ValidationError{}

	// Check field is not empty
	if fg.DbUri == "" {
		newError := shared.ValidationError{
			Tags:       []string{"DB_URI"},
			FieldGroup: fgName,
			Message:    "DB_URI is required.",
		}
		errors = append(errors, newError)
		return errors
	}

	ca := ""
	if fg.DbConnectionArgs.Ssl != nil {
		ca = fg.DbConnectionArgs.Ssl.Ca
	}

	// Connect to database
	err := shared.ValidateDatabaseConnection(opts, fg.DbUri, ca, fg.DbConnectionArgs.Threadlocals, fg.DbConnectionArgs.Autorollback, fg.DbConnectionArgs.SslMode, fg.DbConnectionArgs.SslRootCert, fgName)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"DB_URI"},
			FieldGroup: fgName,
			Message:    "Could not connect to database. Error: " + err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	// Return errors
	return errors

}
