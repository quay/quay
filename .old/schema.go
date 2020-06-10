package lib

/* Required Fields
- PREFERRED_URL_SCHEME
- SERVER_HOSTNAME
- DB_URI
- AUTHENTICATION_TYPE
- DISTRIBUTED_STORAGE_CONFIG
- BUILDLOGS_REDIS
- USER_EVENTS_REDIS
- DISTRIBUTED_STORAGE_PREFERENCE
- DEFAULT_TAG_EXPIRATION
- TAG_EXPIRATION_OPTIONS
*/

// QuayConfig is a struct that holds the schema information for a config.yaml
type QuayConfig struct {
	RegistryState          string   `yaml:"REGISTRY_STATE"                validate:"omitempty,oneof=normal readonly"`
	PreferredURLScheme     string   `yaml:"PREFERRED_URL_SCHEME"          validate:"required,oneof=http https"`
	ServerHostname         string   `yaml:"SERVER_HOSTNAME"               validate:"required,hostname"`
	ExternalTLSTermination bool     `yaml:"EXTERNAL_TLS_TERMINATION"      validate:"omitempty"`
	SSLCiphers             []string `yaml:"SSL_CIPHERS"                   validate:"omitempty"` //NEEDS TO INCLUDE SSL CIPHERS
	SSLProtocols           []string `yaml:"SSL_PROTOCOLS"                 validate:"omitempty,dive,oneof=SSLv2 SSLv3 TLSv1 TLSv1.1 TLSv1.2 TLSv1.3"`
	RegistryTitle          string   `yaml:"REGISTRY_TITLE"                validate:"omitempty"`
	RegistryTitleShort     string   `yaml:"REGISTRY_TITLE_SHORT"          validate:"omitempty"`
}
