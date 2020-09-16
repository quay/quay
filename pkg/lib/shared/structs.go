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
	Hostname    string `default:"" validate:"" json:"hostname,omitempty" yaml:"hostname"`
	Port        int    `default:"{}" validate:"" json:"port,omitempty" yaml:"port"`
	IsSecure    bool   `default:"{}" validate:"" json:"is_secure,omitempty" yaml:"is_secure"`
	StoragePath string `default:"{}" validate:"" json:"storage_path,omitempty" yaml:"storage_path"`
	AccessKey   string `default:"{}" validate:"" json:"access_key,omitempty" yaml:"access_key"`
	SecretKey   string `default:"{}" validate:"" json:"secret_key,omitempty" yaml:"secret_key"`
	BucketName  string `default:"{}" validate:"" json:"bucket_name,omitempty" yaml:"bucket_name"`
}
