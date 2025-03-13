package distributedstorage

import (
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/creasty/defaults"
	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// DistributedStorageFieldGroup represents the DistributedStorageFieldGroup config fields
type DistributedStorageFieldGroup struct {
	DistributedStorageConfig           map[string]*DistributedStorageDefinition `default:"{}" validate:"" json:"DISTRIBUTED_STORAGE_CONFIG,omitempty" yaml:"DISTRIBUTED_STORAGE_CONFIG,omitempty"`
	DistributedStoragePreference       []string                                 `default:"[]" validate:"" json:"DISTRIBUTED_STORAGE_PREFERENCE,omitempty" yaml:"DISTRIBUTED_STORAGE_PREFERENCE,omitempty"`
	DistributedStorageDefaultLocations []string                                 `default:"[]" validate:"" json:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS,omitempty" yaml:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS,omitempty"`
	FeatureStorageReplication          bool                                     `default:"false" validate:"" json:"FEATURE_STORAGE_REPLICATION" yaml:"FEATURE_STORAGE_REPLICATION"`
	FeatureProxyStorage                bool                                     `default:"false" validate:"" json:"FEATURE_PROXY_STORAGE" yaml:"FEATURE_PROXY_STORAGE"`
}

// DistributedStorageDefinition represents a single storage configuration as a tuple (Name, Arguments)
type DistributedStorageDefinition struct {
	Name string                         `default:"" validate:"" json:",inline" yaml:",inline"`
	Args *shared.DistributedStorageArgs `default:"" validate:"" json:",inline" yaml:",inline"`
}

// NewDistributedStorageFieldGroup creates a new DistributedStorageFieldGroup
func NewDistributedStorageFieldGroup(fullConfig map[string]interface{}) (*DistributedStorageFieldGroup, error) {
	newDistributedStorageFieldGroup := &DistributedStorageFieldGroup{}
	defaults.Set(newDistributedStorageFieldGroup)

	if value, ok := fullConfig["FEATURE_STORAGE_REPLICATION"]; ok {
		newDistributedStorageFieldGroup.FeatureStorageReplication, ok = value.(bool)
		if !ok {
			return newDistributedStorageFieldGroup, errors.New("FEATURE_STORAGE_REPLICATION must be of type boolean")
		}
	}

	if value, ok := fullConfig["DISTRIBUTED_STORAGE_PREFERENCE"]; ok {
		for _, element := range value.([]interface{}) {
			strElement, ok := element.(string)
			if !ok {
				return newDistributedStorageFieldGroup, errors.New("DISTRIBUTED_STORAGE_PREFERENCE must be of type []string")
			}

			newDistributedStorageFieldGroup.DistributedStoragePreference = append(
				newDistributedStorageFieldGroup.DistributedStoragePreference,
				strElement,
			)
		}
	}

	if value, ok := fullConfig["DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS"]; ok {
		for _, element := range value.([]interface{}) {
			strElement, ok := element.(string)
			if !ok {
				return newDistributedStorageFieldGroup, errors.New("DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS must be of type []string")
			}

			newDistributedStorageFieldGroup.DistributedStorageDefaultLocations = append(
				newDistributedStorageFieldGroup.DistributedStorageDefaultLocations,
				strElement,
			)
		}
	}

	if value, ok := fullConfig["DISTRIBUTED_STORAGE_CONFIG"]; ok {
		var err error
		value := value.(map[string]interface{})
		for k, v := range value {
			if _, ok := v.([]interface{}); !ok {
				return newDistributedStorageFieldGroup, errors.New("DISTRIBUTED_STORAGE_CONFIG object values must be of form (Name, Args)")
			}

			newDistributedStorageFieldGroup.DistributedStorageConfig[k], err = NewDistributedStorageDefinition(v.([]interface{}))
			if err != nil {
				return newDistributedStorageFieldGroup, err
			}
		}

	}

	return newDistributedStorageFieldGroup, nil
}

// NewDistributedStorageDefinition creates a new DistributedStorageDefinition
func NewDistributedStorageDefinition(storageDef []interface{}) (*DistributedStorageDefinition, error) {
	newDistributedStorageDefinition := &DistributedStorageDefinition{}
	defaults.Set(newDistributedStorageDefinition)

	var ok bool
	var err error
	newDistributedStorageDefinition.Name, ok = storageDef[0].(string)
	if !ok {
		return newDistributedStorageDefinition, errors.New("First index of value in DISTRIBUTED_STORAGE_CONFIG must be a string")
	}

	storageArgs, ok := storageDef[1].(map[string]interface{})
	if !ok {
		return newDistributedStorageDefinition, errors.New("Second index of value in DISTRIBUTED_STORAGE_CONFIG must be an object")
	}

	newDistributedStorageDefinition.Args, err = NewDistributedStorageArgs(storageArgs)
	if err != nil {
		return newDistributedStorageDefinition, err
	}

	return newDistributedStorageDefinition, nil
}

// NewDistributedStorageArgs creates a new DistributedStorageArgs type
func NewDistributedStorageArgs(storageArgs map[string]interface{}) (*shared.DistributedStorageArgs, error) {
	newDistributedStorageArgs := &shared.DistributedStorageArgs{}
	defaults.Set(newDistributedStorageArgs)

	if value, ok := storageArgs["access_key"]; ok {
		newDistributedStorageArgs.AccessKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("access_key must be of type string")
		}
	}

	if value, ok := storageArgs["bucket_name"]; ok {
		newDistributedStorageArgs.BucketName, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("bucket_name must be of type string")
		}
	}

	if value, ok := storageArgs["hostname"]; ok {
		newDistributedStorageArgs.Hostname, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("hostname must be of type string")
		}
	}

	if value, ok := storageArgs["is_secure"]; ok {
		newDistributedStorageArgs.IsSecure, ok = value.(bool)
		if !ok {
			return newDistributedStorageArgs, errors.New("is_secure must be of type boolean")
		}
	}

	if value, ok := storageArgs["port"]; ok {

		switch t := value.(type) {
		case int:
			newDistributedStorageArgs.Port = t
		case string:
			if len(t) == 0 {
				newDistributedStorageArgs.Port = 0
			} else {
				v, err := strconv.Atoi(t)
				if err != nil {
					return newDistributedStorageArgs, errors.New("port must be of type integer")
				}
				newDistributedStorageArgs.Port = v
			}
		case float64:
			newDistributedStorageArgs.Port = int(t)
		default:
			return newDistributedStorageArgs, errors.New("port must be of type integer")
		}

	}

	if value, ok := storageArgs["secret_key"]; ok {
		newDistributedStorageArgs.SecretKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("secret_key must be of type string")
		}
	}

	if value, ok := storageArgs["s3_secret_key"]; ok {
		newDistributedStorageArgs.S3SecretKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("s3_secret_key must be of type string")
		}
	}

	if value, ok := storageArgs["s3_access_key"]; ok {
		newDistributedStorageArgs.S3AccessKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("s3_access_key must be of type string")
		}
	}

	if value, ok := storageArgs["host"]; ok {
		newDistributedStorageArgs.Host, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("host must be of type string")
		}
	}

	if value, ok := storageArgs["s3_bucket"]; ok {
		newDistributedStorageArgs.S3Bucket, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("s3_bucket must be of type string")
		}
	}

	if value, ok := storageArgs["azure_container"]; ok {
		newDistributedStorageArgs.AzureContainer, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("azure_container must be of type string")
		}
	}

	if value, ok := storageArgs["azure_account_name"]; ok {
		newDistributedStorageArgs.AzureAccountName, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("azure_container must be of type string")
		}
	}

	if value, ok := storageArgs["azure_account_key"]; ok {
		newDistributedStorageArgs.AzureAccountKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("azure_account_key must be of type string")
		}
	}

	if value, ok := storageArgs["sas_token"]; ok {
		newDistributedStorageArgs.SASToken, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("sas_token must be of type string")
		}
	}

	if value, ok := storageArgs["endpoint_url"]; ok {
		newDistributedStorageArgs.EndpointURL, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("endpoint_url must be of type string")
		}
	}

	if value, ok := storageArgs["storage_path"]; ok {
		newDistributedStorageArgs.StoragePath, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("storage_path must be of type string")
		}
	}

	if value, ok := storageArgs["cloudfront_distribution_domain"]; ok {
		newDistributedStorageArgs.CloudfrontDistributionDomain, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("cloudfront_distribution_domain must be of type string")
		}
	}

	if value, ok := storageArgs["cloudfront_key_id"]; ok {
		newDistributedStorageArgs.CloudfrontKeyID, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("cloudfront_key_id must be of type string")
		}
	}

	// CloudFlare provider
	if value, ok := storageArgs["cloudflare_domain"]; ok {
		newDistributedStorageArgs.CloudflareDomain, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("cloudflare_domain must be of type string")
		}
	}

	// Multi CDN provider
	if value, ok := storageArgs["storage_config"]; ok {
		newDistributedStorageArgs.StorageConfig, ok = value.(map[string]interface{})
		if !ok {
			return newDistributedStorageArgs, errors.New("storage_config must be of type map[string]string")
		}
	}

	if value, ok := storageArgs["providers"]; ok {
		newDistributedStorageArgs.Providers, ok = value.(map[string]interface{})
		if !ok {
			return newDistributedStorageArgs, errors.New("providers must be of type map[string]string")
		}
	}

	if value, ok := storageArgs["default_provider"]; ok {
		newDistributedStorageArgs.DefaultProvider, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("default_provider must be of type string")
		}
	}

	if value, ok := storageArgs["auth_version"]; ok {

		switch t := value.(type) {
		case int:
			newDistributedStorageArgs.SwiftAuthVersion = t
		case string:
			if len(t) == 0 {
				newDistributedStorageArgs.SwiftAuthVersion = 0
			} else {
				v, err := strconv.Atoi(t)
				if err != nil {
					return newDistributedStorageArgs, errors.New("auth_version must be of type integer")
				}
				newDistributedStorageArgs.SwiftAuthVersion = v
			}
		case float64:
			newDistributedStorageArgs.SwiftAuthVersion = int(t)
		default:
			return newDistributedStorageArgs, errors.New("auth_version must be of type integer")
		}

	}

	if value, ok := storageArgs["auth_url"]; ok {
		newDistributedStorageArgs.SwiftAuthURL, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("auth_url must be of type string")
		}
	}

	if value, ok := storageArgs["swift_container"]; ok {
		newDistributedStorageArgs.SwiftContainer, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("swift_container must be of type string")
		}
	}

	if value, ok := storageArgs["swift_user"]; ok {
		newDistributedStorageArgs.SwiftUser, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("swift_user must be of type string")
		}
	}

	if value, ok := storageArgs["swift_password"]; ok {
		newDistributedStorageArgs.SwiftPassword, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("swift_password must be of type string")
		}
	}

	if value, ok := storageArgs["ca_cert_path"]; ok {
		newDistributedStorageArgs.SwiftCaCertPath, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("ca_cert_path must be of type string")
		}
	}

	if value, ok := storageArgs["temp_url_key"]; ok {
		newDistributedStorageArgs.SwiftTempURLKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("temp_url_key must be of type string")
		}
	}

	if value, ok := storageArgs["os_options"]; ok {
		newDistributedStorageArgs.SwiftOsOptions, ok = value.(map[string]interface{})
		if !ok {
			return newDistributedStorageArgs, errors.New("os_options must be an object")
		}
	}

	if value, ok := storageArgs["sts_role_arn"]; ok {
		newDistributedStorageArgs.STSRoleArn, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("sts_role_arn must be a string")
		}
	}

	if value, ok := storageArgs["sts_user_access_key"]; ok {
		newDistributedStorageArgs.STSUserAccessKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("sts_user_access_key must be a string")
		}
	}

	if value, ok := storageArgs["sts_user_secret_key"]; ok {
		newDistributedStorageArgs.STSUserSecretKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("sts_user_secret_key must be a string")
		}
	}

	if value, ok := storageArgs["sts_web_token_filen"]; ok {
		newDistributedStorageArgs.STSWebIdentityTokenFile, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("sts_web_token_file must be a string")
		}
	}

	return newDistributedStorageArgs, nil
}

func (ds DistributedStorageDefinition) UnmarshalJSON(buf []byte) error {
	tmp := []interface{}{&ds.Name, &ds.Args}
	wantLen := len(tmp)
	if err := json.Unmarshal(buf, &tmp); err != nil {
		return err
	}
	if g, e := len(tmp), wantLen; g != e {
		return fmt.Errorf("wrong number of fields in DistributedStorage: %d != %d", g, e)
	}
	return nil
}

func (ds DistributedStorageDefinition) MarshalJSON() ([]byte, error) {
	return json.Marshal([]interface{}{&ds.Name, &ds.Args})
}
