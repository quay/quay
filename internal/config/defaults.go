package config

// Default values for Quay configuration fields.
const (
	DefaultPreferredURLScheme = "http"
	DefaultRegistryTitle      = "Red Hat Quay"
	DefaultAuthenticationType = "Database"
	DefaultTagExpiration      = "2w"
)

// newDefaultConfig returns a Config pre-populated with Quay's documented
// defaults. YAML unmarshal overwrites only fields present in the input,
// so unset fields retain these defaults.
func newDefaultConfig() Config {
	return Config{
		Server: Server{
			PreferredURLScheme: DefaultPreferredURLScheme,
			RegistryTitle:      DefaultRegistryTitle,
			RegistryTitleShort: DefaultRegistryTitle,
		},
		Auth: Auth{
			AuthenticationType: DefaultAuthenticationType,
		},
		Storage: Storage{
			DefaultTagExpiration: DefaultTagExpiration,
		},
		Features: Features{
			FeatureDirectLogin:         boolPtr(true),
			FeatureUserCreation:        boolPtr(true),
			FeatureAnonymousAccess:     boolPtr(true),
			FeatureChangeTagExpiration: boolPtr(true),
			FeatureAppSpecificTokens:   boolPtr(true),
		},
	}
}

// boolPtr returns a pointer to b.
func boolPtr(b bool) *bool {
	return &b
}
