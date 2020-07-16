package distributedstorage

import (
	"encoding/json"
	"fmt"
)

type DistributedStorageFieldGroup struct {
	DistributedStorageConfig           map[string]DistributedStorage `default:"{}" validate:"" json:"DISTRIBUTED_STORAGE_CONFIG" yaml:"DISTRIBUTED_STORAGE_CONFIG"`
	DistributedStoragePreference       []string                      `default:"[default]" validate:"" json:"DISTRIBUTED_STORAGE_PREFERENCE" yaml:"DISTRIBUTED_STORAGE_PREFERENCE"`
	DistributedStorageDefaultLocations []string                      `default:"[default]" validate:"" json:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS" yaml:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS"`
}

type DistributedStorage struct {
	Name string                 `default:"" validate:"" json:",inline" yaml:",inline"`
	Args DistributedStorageArgs `default:"" validate:"" json:",inline" yaml:",inline"`
}

func (ds DistributedStorage) UnmarshalJSON(buf []byte) error {
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

func (ds DistributedStorage) MarshalJSON() ([]byte, error) {
	return json.Marshal([]interface{}{&ds.Name, &ds.Args})
}

type DistributedStorageArgs struct {
	Hostname    string `default:"" validate:"" json:"hostname" yaml:"hostname"`
	Port        int    `default:"{}" validate:"" json:"port" yaml:"port"`
	IsSecure    bool   `default:"{}" validate:"" json:"is_secure" yaml:"is_secure"`
	StoragePath string `default:"{}" validate:"" json:"storage_path" yaml:"storage_path"`
	AccessKey   string `default:"{}" validate:"" json:"access_key" yaml:"access_key"`
	SecretKey   string `default:"{}" validate:"" json:"secret_key" yaml:"secret_key"`
	BucketName  string `default:"{}" validate:"" json:"bucket_name" yaml:"bucket_name"`
}
