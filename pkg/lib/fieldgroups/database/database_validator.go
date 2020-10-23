package database

import (
	"crypto/tls"
	"crypto/x509"
	"database/sql"
	"errors"
	"fmt"
	"io/ioutil"
	"net"
	"net/url"

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
	err = ValidateDatabaseConnection(opts, uri, ca)
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
func ValidateDatabaseConnection(opts shared.Options, uri *url.URL, caCert string) error {

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
	if scheme == "mysql+pymysql" {

		// Create db connection string
		dsn := credentials + "@tcp(" + fullHostName + ")/" + dbname

		// Check if CA cert is used
		if caCert != "" {
			certBytes, err := ioutil.ReadFile(caCert)
			if err != nil {
				return err
			}
			caCertPool := x509.NewCertPool()
			if ok := caCertPool.AppendCertsFromPEM(certBytes); !ok {
				return errors.New("Could not add CA cert to pool")
			}
			tlsConfig := &tls.Config{
				InsecureSkipVerify: false,
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

		// Database is Postgres
	} else if scheme == "postgresql" {

		var psqlInfo string
		host, port, err := net.SplitHostPort(fullHostName)
		if err != nil {
			if caCert == "" {
				psqlInfo = fmt.Sprintf("host=%s user=%s password=%s dbname=%s sslmode=disable", fullHostName, user, password, dbname)
			} else {
				psqlInfo = fmt.Sprintf("host=%s user=%s password=%s dbname=%s sslmode=verify-ca sslrootcert=%s", fullHostName, user, password, dbname, caCert)
			}
		} else {
			if caCert == "" {
				psqlInfo = fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbname)
			} else {
				psqlInfo = fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=verify-ca sslrootcert=%s", host, port, user, password, dbname, caCert)
			}

		}

		// Open connection
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

	// If database is postgres, make sure that extension pg_trgm is installed
	if scheme == "postgresql" {
		rows, err := db.Query("SELECT extname FROM pg_extension")
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var ext string
			if err := rows.Scan(&ext); err != nil {
				return err
			}
			if ext == "pg_trgm" {
				return nil
			}
		}
		return errors.New("If you are using a Postgres database, you must install the pg_trgm extension")
	}

	// Return no error
	return nil

}
