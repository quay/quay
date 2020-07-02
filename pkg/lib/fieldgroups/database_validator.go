package fieldgroups

import (
	"database/sql"
	"net/url"

	_ "github.com/go-sql-driver/mysql" //mysql driver
	_ "github.com/lib/pq"              // postgres driver
)

// Validate checks the configuration settings for this field group
func (fg *DatabaseFieldGroup) Validate() []ValidationError {

	// Make empty errors
	errors := []ValidationError{}

	// Check field is not empty
	if fg.DbUri == "" {
		newError := ValidationError{
			Tags:    []string{"DB_URI"},
			Policy:  "A is Required",
			Message: "DB_URI is required.",
		}
		errors = append(errors, newError)
		return errors
	}

	// Convert uri into correct format
	uri, err := url.Parse(fg.DbUri)
	if err != nil {
		newError := ValidationError{
			Tags:    []string{"DB_URI"},
			Policy:  "A incorrect format",
			Message: "DB_URI has incorrect format. Must be URI.",
		}
		errors = append(errors, newError)
		return errors
	}

	// Connect to database
	err = ValidateDatabaseConnection(uri)
	if err != nil {
		newError := ValidationError{
			Tags:    []string{"DB_URI"},
			Policy:  "Database Connection",
			Message: "Could not connect to database.",
		}
		errors = append(errors, newError)
		return errors
	}

	// Return errors
	return errors

}

// ValidateDatabaseConnection checks that the Bitbucker OAuth credentials are correct
func ValidateDatabaseConnection(uri *url.URL) error {

	// Get parameters from uri
	scheme := uri.Scheme
	user := uri.User.Username()
	password, _ := uri.User.Password()
	host := uri.Host
	dbname := uri.Path

	// Add tcp to host
	dsn := user + ":" + password + "@tcp(" + host + ")" + dbname

	// Define connection
	db, err := sql.Open(scheme, dsn)
	if err != nil {
		return err
	}

	// Try to ping database
	err = db.Ping()
	if err != nil {
		return err
	}

	// Return no error
	return nil

}
