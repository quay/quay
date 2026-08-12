package config

// Default values for Quay configuration fields.
const (
	DefaultPreferredURLScheme           = "http"
	DefaultRegistryTitle                = "Red Hat Quay"
	DefaultAuthenticationType           = "Database"
	DefaultTagExpiration                = "2w"
	DefaultLibraryNamespace             = "library"
	DefaultLastAccessedUpdateThresholdS = 60
	DefaultInstanceServiceKeyService    = "quay"
	DefaultRegistryJWTAuthMaxFreshS     = 3660

	// Feature defaults mirror the Python configuration defaults. A nil feature
	// value is resolved against these defaults by internal/features.
	DefaultFeatureSuperUsers           = true
	DefaultFeatureSuperUsersFullAccess = false
	DefaultFeatureAnonymousAccess      = true
	DefaultFeatureReferrersAPI         = true
	DefaultFeatureLibrarySupport       = true
	DefaultFeatureUserLastAccessed     = true
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
			LibraryNamespace:   DefaultLibraryNamespace,
		},
		Auth: Auth{
			AuthenticationType: DefaultAuthenticationType,
		},
		Storage: Storage{
			DefaultTagExpiration: DefaultTagExpiration,
		},
		Features: Features{
			FeatureDirectLogin:          true,
			FeatureUserCreation:         true,
			FeatureAnonymousAccess:      DefaultFeatureAnonymousAccess,
			FeatureChangeTagExpiration:  true,
			FeatureAppSpecificTokens:    true,
			FeatureSuperUsers:           DefaultFeatureSuperUsers,
			FeatureSuperUsersFullAccess: DefaultFeatureSuperUsersFullAccess,
			FeatureReferrersAPI:         DefaultFeatureReferrersAPI,
			FeatureLibrarySupport:       DefaultFeatureLibrarySupport,
			FeatureUserLastAccessed:     DefaultFeatureUserLastAccessed,
		},
		AccessLog: AccessLog{
			LastAccessedUpdateThresholdS: DefaultLastAccessedUpdateThresholdS,
		},
		Keys: Keys{
			InstanceServiceKeyService: DefaultInstanceServiceKeyService,
			RegistryJWTAuthMaxFreshS:  DefaultRegistryJWTAuthMaxFreshS,
		},
	}
}
