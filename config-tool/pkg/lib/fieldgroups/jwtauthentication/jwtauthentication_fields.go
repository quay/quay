package jwtauthentication

// Fields returns a list of strings representing the fields in this field group
func (fg *JWTAuthenticationFieldGroup) Fields() []string {
	return []string{"AUTHENTICATION_TYPE", "FEATURE_MAILING", "JWT_AUTH_ISSUER", "JWT_GETUSER_ENDPOINT", "JWT_QUERY_ENDPOINT", "JWT_VERIFY_ENDPOINT"}
}
