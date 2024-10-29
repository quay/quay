package shared

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"net/smtp"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"time"

	goOIDC "github.com/coreos/go-oidc"
	"github.com/go-ldap/ldap/v3"
	"github.com/go-redis/redis/v8"
	"github.com/go-sql-driver/mysql"
	"github.com/jackc/pgx/v4"
	_ "github.com/mattn/go-sqlite3"
	log "github.com/sirupsen/logrus"
	"golang.org/x/oauth2"
)

// ValidateGitHubOAuth checks that the Bitbucker OAuth credentials are correct
func ValidateGitHubOAuth(opts Options, clientID, clientSecret, githubEndpoint string) bool {

	req, err := http.NewRequest("GET", githubEndpoint, nil)
	if err != nil {
		return false
	}
	req.SetBasicAuth(clientID, clientSecret)

	tlsConfig, err := GetTlsConfig(opts)
	if err != nil {
		log.Warning(err)
		return false
	}
	transport := &http.Transport{TLSClientConfig: tlsConfig}
	client := &http.Client{Transport: transport}

	resp, err := client.Do(req)
	if err != nil {
		log.Warning(err)
		return false
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Warning(err)
		return false
	}

	log.Debugf("github response: %d, %s", resp.StatusCode, string(body))

	return resp.StatusCode == 200
}

// ValidateRequiredObject validates that a object input is not nil
func ValidateRequiredObject(input interface{}, field, fgName string) (bool, ValidationError) {

	// Check string
	if input == nil || reflect.ValueOf(input).IsNil() {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " is required",
		}
		return false, newError
	}

	// Return okay
	return true, ValidationError{}

}

// ValidateRequiredString validates that a string input is not empty
func ValidateRequiredString(input, field, fgName string) (bool, ValidationError) {

	// Check string
	if input == "" {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " is required",
		}
		return false, newError
	}

	// Return okay
	return true, ValidationError{}

}

// ValidateAtLeastOneOfBool validates that at least one of the given options is true
func ValidateAtLeastOneOfBool(inputs []bool, fields []string, fgName string) (bool, ValidationError) {

	// At first, assume none are true
	atLeastOne := false

	// Iterate through options
	for _, val := range inputs {
		if val {
			atLeastOne = true
			break
		}
	}

	// If at least one isnt true, return error
	if !atLeastOne {
		newError := ValidationError{
			Tags:       fields,
			FieldGroup: fgName,
			Message:    "At least one of " + strings.Join(fields, ",") + " must be enabled",
		}
		return false, newError
	}

	return true, ValidationError{}

}

// ValidateAtLeastOneOfString validates that at least one of the given options is true
func ValidateAtLeastOneOfString(inputs []string, fields []string, fgName string) (bool, ValidationError) {

	// At first, assume none are true
	atLeastOne := false

	// Iterate through options
	for _, val := range inputs {
		if val != "" {
			atLeastOne = true
			break
		}
	}

	// If at least one isnt true, return error
	if !atLeastOne {
		newError := ValidationError{
			Tags:       fields,
			FieldGroup: fgName,
			Message:    "At least one of " + strings.Join(fields, ",") + " must be present",
		}
		return false, newError
	}

	return true, ValidationError{}

}

// ValidateRedisConnection validates that a Redis connection can successfully be established
func ValidateRedisConnection(options *redis.Options, field, fgName string) (bool, ValidationError) {

	// Start client
	rdb := redis.NewClient(options)
	log.Debugf("Address: %s", options.Addr)
	log.Debugf("Username: %s", options.Username)
	log.Debugf("Password Len: %d", len(options.Password))
	log.Debugf("Ssl: %+v", options.TLSConfig)

	// Ping client
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    "Could not connect to Redis with values provided in " + field + ". Error: " + err.Error(),
		}
		return false, newError
	}

	return true, ValidationError{}

}

// ValidateIsOneOfString validates that a string is one of a given option
func ValidateIsOneOfString(input string, options []string, field string, fgName string) (bool, ValidationError) {

	// At first, assume none are true
	isOneOf := false

	// Iterate through options
	for _, val := range options {
		if input == val {
			isOneOf = true
			break
		}
	}

	// If at least one isnt true, return error
	if !isOneOf {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must be one of " + strings.Join(options, ", ") + ".",
		}
		return false, newError
	}

	return true, ValidationError{}
}

// ValidateIsURL tests a string to determine if it is a well-structured url or not.
func ValidateIsURL(input string, field string, fgName string) (bool, ValidationError) {

	_, err := url.ParseRequestURI(input)
	if err != nil {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must be of type URL",
		}
		return false, newError
	}

	u, err := url.Parse(input)
	if err != nil || u.Scheme == "" || u.Host == "" {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must be of type URL",
		}
		return false, newError
	}

	return true, ValidationError{}
}

// ValidateIsHostname tests a string to determine if it is a well-structured hostname or not.
func ValidateIsHostname(input string, field string, fgName string) (bool, ValidationError) {

	// trim whitespace
	input = strings.Trim(input, " ")

	// check against regex
	re, _ := regexp.Compile(`^[a-zA-Z-0-9\.]+(:[0-9]+)?$`)
	if !re.MatchString(input) {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must be of type Hostname",
		}
		return false, newError
	}

	return true, ValidationError{}
}

// ValidateHostIsReachable will check if a get request returns a 200 status code
func ValidateHostIsReachable(opts Options, input string, field string, fgName string) (bool, ValidationError) {

	log.Debugf("Attempting to reach %s", input)
	// Get protocol
	u, err := url.Parse(input)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
	}

	scheme := u.Scheme

	// Get raw hostname without protocol
	host := strings.TrimPrefix(input, "https://")
	host = strings.TrimPrefix(host, "http://")

	// Set timeout
	timeout := 5 * time.Second

	log.Debugf("Dialing %s with scheme %s", host, scheme)

	// Switch on protocol
	switch scheme {
	case "http":

		_, err := net.DialTimeout("tcp", host, timeout)
		if err != nil {
			newError := ValidationError{
				Tags:       []string{field},
				FieldGroup: fgName,
				Message:    err.Error(),
			}
			return false, newError
		}

	case "https":

		config, err := GetTlsConfig(opts)
		if err != nil {
			newError := ValidationError{
				Tags:       []string{field},
				FieldGroup: fgName,
				Message:    err.Error(),
			}
			return false, newError
		}
		dialer := &net.Dialer{
			Timeout: timeout,
		}

		_, err = tls.DialWithDialer(dialer, "tcp", host, config)
		if err != nil {
			newError := ValidationError{
				Tags:       []string{field},
				FieldGroup: fgName,
				Message:    "Cannot reach " + input + ". Error: " + err.Error(),
			}
			return false, newError
		}

	default:
		return false, ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must have a valid scheme",
		}
	}

	return true, ValidationError{}

}

// ValidateFileExists will check if a path exists on the current machine
func ValidateFileExists(input string, field string, fgName string) (bool, ValidationError) {

	// Check path
	if _, err := os.Stat(input); os.IsNotExist(err) {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    "Cannot access the file " + input,
		}
		return false, newError
	}

	return true, ValidationError{}

}

// ValidateTimePattern validates that a string has the pattern ^[0-9]+(w|m|d|h|s)$
func ValidateTimePattern(input string, field string, fgName string) (bool, ValidationError) {

	re := regexp.MustCompile(`^[0-9]+(w|m|d|h|s)$`)
	matches := re.FindAllString(input, -1)

	// If the pattern is not matched
	if len(matches) != 1 {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must have the regex pattern ^[0-9]+(w|m|d|h|s)$",
		}
		return false, newError
	}

	return true, ValidationError{}
}

// ValidateCertsPresent validates that all required certificates are present in the options struct
func ValidateCertsPresent(opts Options, requiredCertNames []string, fgName string) (bool, ValidationError) {

	// If no certificates are passed
	if opts.Certificates == nil {
		newError := ValidationError{
			Tags:       []string{"Certificates"},
			FieldGroup: fgName,
			Message:    "Certificates are required for SSL but are not present",
		}
		return false, newError
	}

	// Check that all required certificates are present
	for _, certName := range requiredCertNames {

		// Check that cert has been included
		if _, ok := opts.Certificates[certName]; !ok {
			newError := ValidationError{
				Tags:       []string{"Certificates"},
				FieldGroup: fgName,
				Message:    "Certificate " + certName + " is required for " + fgName + " .",
			}
			return false, newError
		}
	}

	return true, ValidationError{}

}

// ValidateCertPairWithHostname will validate that a public private key pair are valid and have the correct hostname
func ValidateCertPairWithHostname(cert, key []byte, hostname string, fgName string) (bool, ValidationError) {

	// Load key pair, this will check the public, private keys are paired
	certChain, err := tls.X509KeyPair(cert, key)
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"Certificates"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
		return false, newError
	}

	certificate, err := x509.ParseCertificate(certChain.Certificate[0])
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"Certificates"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
		return false, newError
	}

	// Make sure port is removed
	cleanHost, _, err := net.SplitHostPort(hostname)
	if err != nil {
		cleanHost = hostname
	}

	err = certificate.VerifyHostname(cleanHost)
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"Certificates"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
		return false, newError
	}

	return true, ValidationError{}

}

// ValidateBitbucketOAuth checks that the Bitbucker OAuth credentials are correct
func ValidateBitbucketOAuth(clientID, clientSecret string) bool {

	// Generated by curl-to-Go: https://mholt.github.io/curl-to-go
	body := strings.NewReader(`grant_type=authorization_code&code={code}`)
	req, _ := http.NewRequest("POST", "https://bitbucket.org/site/oauth2/access_token", body)

	req.SetBasicAuth(clientID, clientSecret)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		log.Warning(err)
		return false
	}

	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Warning(err)
		return false
	}

	log.Debugf("bitbucket response: %d, %s", resp.StatusCode, string(respBody))
	// Load response into json
	var responseJSON map[string]interface{}
	_ = json.Unmarshal(respBody, &responseJSON)

	// If the error isnt unauthorized
	return responseJSON["error_description"] == "The specified code is not valid."

}

// ValidateDatabaseConnection checks whether database is available
func ValidateDatabaseConnection(opts Options, rawURI, caCert string, threadlocals, autorollback bool, sslmode, sslrootcert, fgName string) error {

	// Convert uri into correct format
	uri, err := url.Parse(rawURI)
	if err != nil {
		return err
	}

	credentials, err := url.PathUnescape(uri.User.String())
	if err != nil {
		return err
	}

	// Get database type
	scheme := uri.Scheme
	fullHostName := uri.Host
	dbname := uri.Path[1:]
	params := uri.Query()

	log.Debugf("Scheme: %s", scheme)
	log.Debugf("Host: %s", fullHostName)
	log.Debugf("Db: %s", dbname)
	log.Debugf("Params: %s", params.Encode())

	if sslmode != "" {
		params.Add("sslmode", sslmode)
	}

	// Database is MySQL
	if scheme == "mysql+pymysql" {

		// Create db connection string
		dsn := credentials + "@tcp(" + fullHostName + ")/" + dbname

		// Check if CA cert is used
		if caCert != "" {
			log.Debug("CA Cert provided")
			relativePath, err := filepath.Rel("conf/stack", caCert)
			if err != nil {
				return err
			}
			certBytes, ok := opts.Certificates[relativePath]
			if !ok {
				return errors.New("could not find " + relativePath + " in config bundle")
			}
			caCertPool := x509.NewCertPool()
			if ok := caCertPool.AppendCertsFromPEM(certBytes); !ok {
				return errors.New("could not add CA cert to pool")
			}
			tlsConfig := &tls.Config{
				InsecureSkipVerify: true,
				RootCAs:            caCertPool,
			}
			mysql.RegisterTLSConfig("custom-tls", tlsConfig)
			log.Debug("Created tls config for database successfully")

			// Add param
			params.Add("tls", "custom-tls")
		}

		log.Debugf("Including params %s", params.Encode())
		dsn = fmt.Sprintf("%s?%s", dsn, params.Encode())

		db, err := sql.Open("mysql", dsn)
		if err != nil {
			return err
		}

		defer db.Close()

		// Try to ping database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		log.Debugf("Pinging database at hostname: %s.", fullHostName)
		err = db.PingContext(ctx)
		if err != nil {
			return err
		}

		var version string
		row := db.QueryRow("SELECT version()")
		err = row.Scan(&version)
		if err != nil {
			return err
		}
		log.Debugf("Database version: %s", version)

		// Database is Postgres
	} else if scheme == "postgresql" {

		// Try to ping database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		// If CA cert was included
		// Check if sslmode is either "verify-full" or "verify-ca"
		// If that's the case, then postgres needs sslrootcert in order to verify
		// the CA against the server (defaults to ~/.postgresql/root.crt)
		// In our case, we will temporarily write the database.pem in /tmp
		// For the actual bundle, the value of sslrootcert should be conf/stack/database.pem
		// Ref: https://www.postgresql.org/docs/9.1/libpq-ssl.html
		if sslmode == "verify-full" || sslmode == "verify-ca" {
			params.Add("sslrootcert", sslrootcert)
		}

		var dsn string
		username := uri.User.Username()
		password, present := uri.User.Password()

		log.Debugf("Including params %s", params.Encode())
		if present {
			dsn = fmt.Sprint(&url.URL{
				Scheme:   scheme,
				User:     url.UserPassword(username, password),
				Host:     fullHostName,
				RawPath:  dbname,
				Path:     "/" + dbname,
				RawQuery: params.Encode(),
			})
		} else {
			dsn = fmt.Sprint(&url.URL{
				Scheme:   scheme,
				User:     url.User(username),
				Host:     fullHostName,
				Path:     "/" + dbname,
				RawQuery: params.Encode(),
			})
		}

		// Connect and defer closing
		log.Debugf("Pinging database at hostname: %s.", fullHostName)
		conn, err := pgx.Connect(ctx, dsn)
		if err != nil {
			return err
		}
		defer conn.Close(ctx)

		// Get version
		var version string
		row := conn.QueryRow(ctx, "SHOW server_version;")
		err = row.Scan(&version)
		if err != nil {
			return err
		}
		log.Debugf("Database version: %s", version)

		// Extract major version number using regex
		var re = regexp.MustCompile(`^(\d+)`)
		match := re.FindStringSubmatch(version)

		if len(match) < 1 {
			// If no match, return an error
			return fmt.Errorf("could not parse major version from: %s", version)
		}

		// Parse the major version as an integer
		majorVersion, err := strconv.Atoi(match[0])
		if err != nil {
			return err
		}

		// Check version
		if majorVersion < 13 {
			log.Warnf("Warning: Your version of PostgreSQL (%s) is EOL (End Of Life). Consider upgrading.", strconv.Itoa(majorVersion))
		}

		// If database is postgres, make sure that extension pg_trgm is installed
		rows, err := conn.Query(ctx, `SELECT extname FROM pg_extension`)
		if err != nil {
			return err
		}

		for rows.Next() {
			var extension string
			err = rows.Scan(&extension)
			if err != nil {
				return err
			}
			fmt.Println(extension)
			if strings.Contains(extension, "pg_trgm") {
				return nil
			}
		}
		return errors.New("if you are using a Postgres database, you must install the pg_trgm extension")

	} else if scheme == "sqlite" {
		// Open a connection to the SQLite database
		db, err := sql.Open("sqlite3", dbname)
		if err != nil {
			return fmt.Errorf("error connecting to sqlite database: %s", err)
		}
		defer db.Close()

		// Try to ping database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		log.Debugf("Pinging sqlite database at %s db path:", dbname)
		err = db.PingContext(ctx)
		if err != nil {
			return err
		}

	} else {
		return errors.New("you must use a valid scheme")
	}

	// Return no error
	return nil

}

// ValidateElasticSearchCredentials will validate credentials
func ValidateElasticSearchCredentials(url, accessKey, accessSecret string) bool {

	// Generated by curl-to-Go: https://mholt.github.io/curl-to-go
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		fmt.Println("o", err.Error())
	}
	req.SetBasicAuth(accessKey, accessSecret)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		fmt.Println("e", err.Error())
	}

	if resp.StatusCode != 200 {
		return false
	}

	return true
}

// ValidateEmailServer validates that the provided smtp server is valid
func ValidateEmailServer(opts Options, mailServer string, mailPort int, useTLS bool, useAuth bool, username string, password string, fgName string) (bool, ValidationError) {

	// Dial smtp server
	conn, err := net.DialTimeout("tcp", mailServer+":"+strconv.Itoa(int(mailPort)), 3*time.Second)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"MAIL_SERVER"},
			FieldGroup: fgName,
			Message:    "Cannot reach " + mailServer + ". Error: " + err.Error(),
		}
	}

	client, err := smtp.NewClient(conn, mailServer)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"MAIL_SERVER"},
			FieldGroup: fgName,
			Message:    "Cannot reach " + mailServer + ". Error: " + err.Error(),
		}
	}

	// If TLS is enabled.
	if useTLS {
		config, err := GetTlsConfig(opts)
		if err != nil {
			return false, ValidationError{
				Tags:       []string{"MAIL_USE_TLS"},
				FieldGroup: fgName,
				Message:    err.Error(),
			}

		}
		config.ServerName = mailServer

		err = client.StartTLS(config)
		if err != nil {
			return false, ValidationError{
				Tags:       []string{"MAIL_USE_TLS"},
				FieldGroup: fgName,
				Message:    err.Error(),
			}

		}
		return true, ValidationError{}
	}

	// If auth is enabled, try to authenticate
	if useAuth {
		auth := smtp.PlainAuth("", username, password, mailServer)
		if err = client.Auth(auth); err != nil {
			return false, ValidationError{
				Tags:       []string{"MAIL_SERVER"},
				FieldGroup: fgName,
				Message:    "Error: " + err.Error(),
			}
		}
	}

	return true, ValidationError{}

}

// ValidateGitLabOAuth checks that the Bitbucker OAuth credentials are correct
func ValidateGitLabOAuth(clientID, clientSecret, gitlabEndpoint string) bool {

	// Generated by curl-to-Go: https://mholt.github.io/curl-to-go

	// Add trailing slash if it doesn't exist
	if string(gitlabEndpoint[len(gitlabEndpoint)-1]) != "/" {
		gitlabEndpoint = gitlabEndpoint + "/"
	}

	req, err := http.NewRequest("POST", gitlabEndpoint+"oauth/token?client_id="+clientID+"&client_secret="+clientSecret+"&grant_type=authorization_code&code=FAKECODE&redirect_uri=REDIRECT_URI", nil)
	if err != nil {
		return false
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	respBody, _ := ioutil.ReadAll(resp.Body)

	// Load response into json
	var responseJSON map[string]interface{}
	_ = json.Unmarshal(respBody, &responseJSON)

	// If the error isnt unauthorized
	return responseJSON["error"] == "invalid_grant"

}

// ValidateGoogleOAuth checks that the Bitbucker OAuth credentials are correct
func ValidateGoogleOAuth(clientID, clientSecret string) bool {

	// Generated by curl-to-Go: https://mholt.github.io/curl-to-go

	req, err := http.NewRequest("POST", "https://www.googleapis.com/oauth2/v3/token?client_id="+clientID+"&client_secret="+clientSecret+"&grant_type=authorization_code&code=FAKECODE&redirect_uri=https://fakeredirect.com", nil)
	if err != nil {
		return false
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	respBody, _ := ioutil.ReadAll(resp.Body)

	// Load response into json
	var responseJSON map[string]interface{}
	_ = json.Unmarshal(respBody, &responseJSON)

	// If the error isnt unauthorized
	return responseJSON["error"] == "invalid_grant"

}

// ValidateLDAPServer validates that the provided ldap server is valid
func ValidateLDAPServer(opts Options, ldapUri, ldapAdminDn, ldapAdminPasswd, ldapUidAttr, ldapEmailAttr, ldapUserFilter string, ldapBaseDn []interface{}, fgName string) (bool, ValidationError) {

	// Get tls config
	tlsConfig, err := GetTlsConfig(opts)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"LDAP"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
	}

	// Check for LDAP ca cert and add if present
	if crt, ok := opts.Certificates["ldap.crt"]; ok {
		certAdded := tlsConfig.RootCAs.AppendCertsFromPEM(crt)
		if !certAdded {
			return false, ValidationError{
				Tags:       []string{"LDAP"},
				FieldGroup: fgName,
				Message:    "Could not successfully load ldap.crt",
			}
		}
	}

	// Dial ldap server
	l, err := ldap.DialURL(ldapUri, ldap.DialWithTLSConfig(tlsConfig))
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not connect to " + ldapUri + ". Error: " + err.Error(),
		}
	}

	// Authenticate
	err = l.Bind(ldapAdminDn, ldapAdminPasswd)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not authenticate LDAP server. Error: " + err.Error(),
		}
	}

	userFilter := fmt.Sprintf("(&(%s=*)%s)", ldapUidAttr, ldapUserFilter)
	request := &ldap.SearchRequest{
		BaseDN: strings.Join(InterfaceArrayToStringArray(ldapBaseDn), ","),
		Scope:  ldap.ScopeWholeSubtree,
		Filter: userFilter,
		Attributes: []string{
			ldapEmailAttr, ldapUidAttr,
		},
		Controls: []ldap.Control{ldap.NewControlPaging(32)},
	}

	_, err = l.Search(request)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not query LDAP server. Error: " + err.Error(),
		}
	}

	return true, ValidationError{}

}

// ValidateOIDCServer validates that the provided oidc server is valid
func ValidateOIDCServer(opts Options, oidcServer, clientID, clientSecret, serviceName string, loginScopes []interface{}, fgName string) (bool, ValidationError) {

	// Create http client
	config, err := GetTlsConfig(opts)
	if err != nil {
		return false, ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
	}
	tr := &http.Transport{TLSClientConfig: config}
	client := &http.Client{Transport: tr, Timeout: 5 * time.Second}

	// Try to ping database
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	ctx = goOIDC.ClientContext(ctx, client)

	if !strings.HasSuffix(oidcServer, "/") {
		return false, ValidationError{
			Tags:       []string{"OIDC_SERVER"},
			FieldGroup: fgName,
			Message:    "OIDC_SERVER must end with a trailing /",
		}
	}

	// Create provider
	p, err := goOIDC.NewProvider(ctx, oidcServer)
	if err != nil {
		p, err = goOIDC.NewProvider(ctx, strings.TrimSuffix(oidcServer, "/"))
		if err != nil {
			return false, ValidationError{
				Tags:       []string{"OIDC_SERVER"},
				FieldGroup: fgName,
				Message:    "Could not create provider for " + serviceName + ". Error: " + err.Error(),
			}
		}
	}

	oauth2Config := oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		Endpoint:     p.Endpoint(),
		RedirectURL:  "http://quay/oauth2/auth0/callback",
		Scopes:       InterfaceArrayToStringArray(loginScopes),
	}

	_, err = oauth2Config.Exchange(ctx, "badcode")
	if err != nil {
		if strings.Contains(err.Error(), "access_denied") {
			return false, ValidationError{
				Tags:       []string{"OIDC_SERVER"},
				FieldGroup: fgName,
				Message:    fmt.Sprintf("Incorrect credentials for OIDC %s", serviceName),
			}
		} else if strings.Contains(err.Error(), "invalid_grant") {
			return true, ValidationError{} // this means we connected to the server correctly
		} else {
			return false, ValidationError{
				Tags:       []string{"OIDC_SERVER"},
				FieldGroup: fgName,
				Message:    "Could not reach OIDC server " + serviceName + ". Error: " + err.Error(),
			}
		}
	}

	return true, ValidationError{}

}

// ValidateDefaultAutoPruneKey validates that DEFAULT_NAMESPACE_AUTOPRUNE_POLICY has key of `number_of_tags` or `creation_date`
func ValidateDefaultAutoPruneKey(input string, field string, fgName string) (bool, ValidationError) {

	re := regexp.MustCompile(`^number_of_tags|creation_date$`)
	matches := re.FindAllString(input, -1)

	// If the pattern is not matched
	if len(matches) != 1 {
		newError := ValidationError{
			Tags:       []string{field},
			FieldGroup: fgName,
			Message:    field + " must have method key with value `number_of_tags` or `creation_date`",
		}
		return false, newError
	}

	return true, ValidationError{}
}
