package lib

// FlaskFieldGroup is a FieldGroup representing the Flask configuration
type FlaskFieldGroup struct {
	JSONifyPrettyPrintRegular bool   `default:"false" yaml:"JSONIFY_PRETTYPRINT_REGLAR"`
	SessionCookieSecure       bool   `default:"false" yaml:"SESSION_COOKIE_SECURE"`
	SessionCookieHTTPOnly     bool   `default:"true" yaml:"SESSION_COOKIE_HTTPONLY"`
	SessionCookieSamesite     string `default:"Lax" yaml:"SESSION_COOKIE_SAMESITE"`
	LoggingLevel              string `default:"DEBUG" yaml:"LOGGING_LEVEL"`
	SendFileMaxAgeDefault     int    `default:"0" yaml:"SEND_FILE_MAX_AGE_DEFAULT"`
}

// Validate assures that the field group contains valid settings
func (fg *FlaskFieldGroup) Validate() (bool, error) {
	return true, nil
}
