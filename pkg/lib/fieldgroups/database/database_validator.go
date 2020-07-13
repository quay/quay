package database

import (
	"database/sql"
	"errors"
	"fmt"
	"net"
	"net/url"

	_ "github.com/go-sql-driver/mysql" //mysql driver
	_ "github.com/lib/pq"              // postgres driver
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *DatabaseFieldGroup) Validate() []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// Check field is not empty
	if fg.DbUri == "" {
		newError := shared.ValidationError{
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
		newError := shared.ValidationError{
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
		newError := shared.ValidationError{
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

	// Declare db and error
	var db *sql.DB
	var err error

	// Get database type
	scheme := uri.Scheme

	// Get credentials
	user := uri.User.Username()
	password, _ := uri.User.Password()
	credentials := uri.User.String()

	// Get full host name
	fullHostName := uri.Host

	// Get database name
	dbname := uri.Path[1:]

	// Database is MySQL
	if scheme == "mysql" {

		// Create db client
		dsn := credentials + "@tcp(" + fullHostName + ")/" + dbname
		db, err = sql.Open("mysql", dsn)
		if err != nil {
			return err
		}

		// Database is Postgres
	} else if scheme == "postgresql" {

		var psqlInfo string
		host, port, err := net.SplitHostPort(fullHostName)
		if err != nil {
			// String if there is no port
			psqlInfo = fmt.Sprintf("host=%s user=%s password=%s dbname=%s sslmode=disable", host, user, password, dbname)
		} else {
			// String if there is a port
			psqlInfo = fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbname)
		}

		db, err = sql.Open("postgres", psqlInfo)
		if err != nil {
			return err
		}

	} else {
		return errors.New("You must use a valid scheme")
	}
	defer db.Close()

	// Try to ping database
	err = db.Ping()
	if err != nil {
		return err
	}

	// Return no error
	return nil

}
