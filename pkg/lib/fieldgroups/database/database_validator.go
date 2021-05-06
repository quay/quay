package database

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/go-pg/pg/v10"
	mysql "github.com/go-sql-driver/mysql" //mysql driver
	_ "github.com/lib/pq"                  // postgres driver
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

	// Convert uri into correct format
	uri, err := url.Parse(fg.DbUri)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"DB_URI"},
			FieldGroup: fgName,
			Message:    "DB_URI has incorrect format. Must be URI.",
		}
		errors = append(errors, newError)
		return errors
	}

	ca := ""
	if fg.DbConnectionArgs.Ssl != nil {
		ca = fg.DbConnectionArgs.Ssl.Ca
	}
	// Connect to database
	err = ValidateDatabaseConnection(opts, uri, fg.DbUri, ca)
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

// ValidateDatabaseConnection checks that the Bitbucker OAuth credentials are correct
func ValidateDatabaseConnection(opts shared.Options, uri *url.URL, rawURI, caCert string) error {

	// Declare db and error
	var db *sql.DB
	var err error

	// Get database type
	scheme := uri.Scheme

	// Get credentials
	credentials := uri.User.String()

	// Get full host name
	fullHostName := uri.Host

	// Get database name
	dbname := uri.Path[1:]

	// Database is MySQL
	if scheme == "mysql+pymysql" {

		// Create db connection string
		dsn := credentials + "@tcp(" + fullHostName + ")/" + dbname

		// Check if CA cert is used
		if caCert != "" {
			certBytes, ok := opts.Certificates["database.pem"]
			if !ok {
				return errors.New("Could not find database.pem in config bundle")
			}
			caCertPool := x509.NewCertPool()
			if ok := caCertPool.AppendCertsFromPEM(certBytes); !ok {
				return errors.New("Could not add CA cert to pool")
			}
			tlsConfig := &tls.Config{
				InsecureSkipVerify: true,
				RootCAs:            caCertPool,
			}

			mysql.RegisterTLSConfig("custom-tls", tlsConfig)
			dsn = fmt.Sprintf("%s?tls=custom-tls", dsn)
		}

		// Open connection
		db, err = sql.Open("mysql", dsn)
		if err != nil {
			return err
		}

		defer db.Close()

		// Try to ping database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		err = db.PingContext(ctx)
		if err != nil {
			return err
		}

		// Database is Postgres
	} else if scheme == "postgresql" {

		// Create connection options
		dbOpts, err := pg.ParseURL(rawURI)
		if err != nil {
			return err
		}

		// If CA cert was included
		if caCert != "" {
			certBytes, ok := opts.Certificates["database.pem"]
			if !ok {
				return errors.New("could not find database.pem in config bundle")
			}
			caCertPool := x509.NewCertPool()
			if ok := caCertPool.AppendCertsFromPEM(certBytes); !ok {
				return errors.New("could not add CA cert to pool")
			}
			tlsConfig := &tls.Config{
				InsecureSkipVerify: true,
				RootCAs:            caCertPool,
			}
			dbOpts.TLSConfig = tlsConfig
		}

		// If no SSL cert is provided
		if caCert == "" && uri.Query().Get("sslmode") != "required" {
			dbOpts.TLSConfig = nil
		}

		// Connect and defer closing
		db := pg.Connect(dbOpts)
		defer db.Close()

		// If database is postgres, make sure that extension pg_trgm is installed
		var extensions string
		_, err = db.Query(pg.Scan(&extensions), `SELECT extname FROM pg_extension`)
		if err != nil {
			return err
		}
		if !strings.Contains(extensions, "pg_trgm") {
			return errors.New("if you are using a Postgres database, you must install the pg_trgm extension")
		}

	} else {
		return errors.New("you must use a valid scheme")
	}

	// Return no error
	return nil

}
