package config

// Features holds the effective FEATURE_* settings used by the Go application.
type Features struct {
	FeatureMailing              bool `yaml:"FEATURE_MAILING"`
	FeatureBuildSupport         bool `yaml:"FEATURE_BUILD_SUPPORT"`
	FeatureSecurityScanner      bool `yaml:"FEATURE_SECURITY_SCANNER"`
	FeatureAnonymousAccess      bool `yaml:"FEATURE_ANONYMOUS_ACCESS"`
	FeatureDirectLogin          bool `yaml:"FEATURE_DIRECT_LOGIN"`
	FeatureUserCreation         bool `yaml:"FEATURE_USER_CREATION"`
	FeatureRepoMirror           bool `yaml:"FEATURE_REPO_MIRROR"`
	FeatureStorageReplication   bool `yaml:"FEATURE_STORAGE_REPLICATION"`
	FeatureProxyStorage         bool `yaml:"FEATURE_PROXY_STORAGE"`
	FeatureChangeTagExpiration  bool `yaml:"FEATURE_CHANGE_TAG_EXPIRATION"`
	FeatureAppSpecificTokens    bool `yaml:"FEATURE_APP_SPECIFIC_TOKENS"`
	FeatureSuperUsers           bool `yaml:"FEATURE_SUPER_USERS"`
	FeatureSuperUsersFullAccess bool `yaml:"FEATURE_SUPERUSERS_FULL_ACCESS"`
	FeatureOrgSharedEmail       bool `yaml:"FEATURE_ORG_SHARED_EMAIL"`
	FeatureReferrersAPI         bool `yaml:"FEATURE_REFERRERS_API"`
	FeatureLibrarySupport       bool `yaml:"FEATURE_LIBRARY_SUPPORT"`
	FeatureUserLastAccessed     bool `yaml:"FEATURE_USER_LAST_ACCESSED"`
}

// HasFullSuperuserAccess reports whether both superuser feature flags are
// enabled.
func (f Features) HasFullSuperuserAccess() bool {
	return f.FeatureSuperUsers && f.FeatureSuperUsersFullAccess
}
