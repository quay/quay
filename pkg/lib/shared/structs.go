package shared

// Options is a struct that tells the validator how to validate
type Options struct {
	Mode         string // One of Online, Offline, Testing
	Certificates map[string][]byte
}

// ValidationError is a struct that holds information about a failed field group policy
type ValidationError struct {
	FieldGroup string
	Tags       []string
	Message    string
}

func (ve ValidationError) String() string {
	return ve.Message
}

// DistributedStorageArgs
type DistributedStorageArgs struct {
	// Args for RHOCSStorage, RadosGWStorage
	Hostname    string `default:"" validate:"" json:"hostname,omitempty" yaml:"hostname,omitempty"`
	Port        int    `default:"" validate:"" json:"port,omitempty" yaml:"port,omitempty"`
	IsSecure    bool   `default:"" validate:"" json:"is_secure,omitempty" yaml:"is_secure,omitempty"`
	StoragePath string `default:"" validate:"" json:"storage_path,omitempty" yaml:"storage_path,omitempty"`
	AccessKey   string `default:"" validate:"" json:"access_key,omitempty" yaml:"access_key,omitempty"`
	SecretKey   string `default:"" validate:"" json:"secret_key,omitempty" yaml:"secret_key,omitempty"`
	BucketName  string `default:"" validate:"" json:"bucket_name,omitempty" yaml:"bucket_name,omitempty"`
	// Args for S3Storage
	S3Bucket    string `default:"" validate:"" json:"s3_bucket,omitempty" yaml:"s3_bucket,omitempty"`
	S3AccessKey string `default:"" validate:"" json:"s3_access_key,omitempty" yaml:"s3_access_key,omitempty"`
	S3SecretKey string `default:"" validate:"" json:"s3_secret_key,omitempty" yaml:"s3_secret_key,omitempty"`
	Host        string `default:"" validate:"" json:"host,omitempty" yaml:"host,omitempty"`
	// Args for AzureStorage
	AzureContainer   string `default:"" validate:"" json:"azure_container,omitempty" yaml:"azure_container,omitempty"`
	AzureAccountName string `default:"" validate:"" json:"azure_account_name,omitempty" yaml:"azure_account_name,omitempty"`
	AzureAccountKey  string `default:"" validate:"" json:"azure_account_key,omitempty" yaml:"azure_account_key,omitempty"`
	SASToken         string `default:"" validate:"" json:"sas_token,omitempty" yaml:"sas_token,omitempty"`
	// Args for Cloudfront
	CloudfrontDistributionDomain string `default:"" validate:"" json:"cloudfront_distribution_domain,omitempty" yaml:"cloudfront_distribution_domain,omitempty"`
	CloudfrontKeyID              string `default:"" validate:"" json:"cloudfront_key_id,omitempty" yaml:"cloudfront_key_id,omitempty"`
	// Args for SwiftStorage
	SwiftAuthVersion int                    `default:"" validate:"" json:"auth_version,omitempty" yaml:"auth_version,omitempty"`
	SwiftAuthURL     string                 `default:"" validate:"" json:"auth_url,omitempty" yaml:"auth_url,omitempty"`
	SwiftContainer   string                 `default:"" validate:"" json:"swift_container,omitempty" yaml:"swift_container,omitempty"`
	SwiftUser        string                 `default:"" validate:"" json:"swift_user,omitempty" yaml:"swift_user,omitempty"`
	SwiftPassword    string                 `default:"" validate:"" json:"swift_password,omitempty" yaml:"swift_password,omitempty"`
	SwiftCaCertPath  string                 `default:"" validate:"" json:"ca_cert_path,omitempty" yaml:"ca_cert_path,omitempty"`
	SwiftTempURLKey  string                 `default:"" validate:"" json:"temp_url_key,omitempty" yaml:"temp_url_key,omitempty"`
	SwiftOsOptions   map[string]interface{} `default:"" validate:"" json:"os_options,omitempty" yaml:"os_options,omitempty"`
}
