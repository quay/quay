package database

import (
	"io/ioutil"
	"os"

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

	sslrootcertTmpPath := fg.DbConnectionArgs.SslRootCert
	if fg.DbConnectionArgs.SslMode == "verify-full" || fg.DbConnectionArgs.SslMode == "verify-ca" {
		// Write database.pem needed for db validation, if any, to a temp file
		tmpCert, err := ioutil.TempFile("/tmp", "database.*.pem")
		if err != nil {
			newError := shared.ValidationError{
				Tags:       []string{"DB_URI"},
				FieldGroup: fgName,
				Message:    "Could write database certificate to temporary file. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return errors
		}

		defer func() {
			tmpCert.Close()
			os.Remove(tmpCert.Name())
		}()

		if _, err := tmpCert.Write(opts.Certificates["database.pem"]); err != nil {
			newError := shared.ValidationError{
				Tags:       []string{"DB_URI"},
				FieldGroup: fgName,
				Message:    "Could write database certificate to temporary file. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return errors
		}

		sslrootcertTmpPath = tmpCert.Name()
	}

	// Connect to database
	err := shared.ValidateDatabaseConnection(opts, fg.DbUri, ca, fg.DbConnectionArgs.Threadlocals, fg.DbConnectionArgs.Autorollback, fg.DbConnectionArgs.SslMode, sslrootcertTmpPath, fgName)
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
