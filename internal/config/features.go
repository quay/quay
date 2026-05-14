package config

// Features holds FEATURE_* flags. Pointer bools distinguish "not set" from "set to false".
type Features struct {
	FeatureMailing             *bool `yaml:"FEATURE_MAILING"`
	FeatureBuildSupport        *bool `yaml:"FEATURE_BUILD_SUPPORT"`
	FeatureSecurityScanner     *bool `yaml:"FEATURE_SECURITY_SCANNER"`
	FeatureAnonymousAccess     *bool `yaml:"FEATURE_ANONYMOUS_ACCESS"`
	FeatureDirectLogin         *bool `yaml:"FEATURE_DIRECT_LOGIN"`
	FeatureUserCreation        *bool `yaml:"FEATURE_USER_CREATION"`
	FeatureRepoMirror          *bool `yaml:"FEATURE_REPO_MIRROR"`
	FeatureStorageReplication  *bool `yaml:"FEATURE_STORAGE_REPLICATION"`
	FeatureProxyStorage        *bool `yaml:"FEATURE_PROXY_STORAGE"`
	FeatureChangeTagExpiration *bool `yaml:"FEATURE_CHANGE_TAG_EXPIRATION"`
	FeatureAppSpecificTokens   *bool `yaml:"FEATURE_APP_SPECIFIC_TOKENS"`
}
