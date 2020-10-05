package distributedstorage

import (
	"encoding/json"
	"errors"
	"fmt"

	"github.com/creasty/defaults"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// DistributedStorageFieldGroup represents the DistributedStorageFieldGroup config fields
type DistributedStorageFieldGroup struct {
	DistributedStorageConfig           map[string]*DistributedStorageDefinition `default:"{}" validate:"" json:"DISTRIBUTED_STORAGE_CONFIG,omitempty" yaml:"DISTRIBUTED_STORAGE_CONFIG,omitempty"`
	DistributedStoragePreference       []string                                 `default:"[]" validate:"" json:"DISTRIBUTED_STORAGE_PREFERENCE,omitempty" yaml:"DISTRIBUTED_STORAGE_PREFERENCE,omitempty"`
	DistributedStorageDefaultLocations []string                                 `default:"[]" validate:"" json:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS,omitempty" yaml:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS,omitempty"`
	FeatureStorageReplication          bool                                     `default:"false" validate:"" json:"FEATURE_STORAGE_REPLICATION,omitempty" yaml:"FEATURE_STORAGE_REPLICATION,omitempty"`
	FeatureProxyStorage                bool                                     `default:"false" validate:"" json:"FEATURE_PROXY_STORAGE,omitempty" yaml:"FEATURE_PROXY_STORAGE,omitempty"`
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
		newDistributedStorageArgs.Port, ok = value.(int)
		if !ok {

			// We must have an extra check for float64
			if v, ok := value.(float64); ok {
				newDistributedStorageArgs.Port = int(v)
			} else {
				return newDistributedStorageArgs, errors.New("port must be of type integer")
			}

		}
	}

	if value, ok := storageArgs["secret_key"]; ok {
		newDistributedStorageArgs.SecretKey, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("secret_key must be of type string")
		}
	}

	if value, ok := storageArgs["storage_path"]; ok {
		newDistributedStorageArgs.StoragePath, ok = value.(string)
		if !ok {
			return newDistributedStorageArgs, errors.New("storage_path must be of type string")
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
