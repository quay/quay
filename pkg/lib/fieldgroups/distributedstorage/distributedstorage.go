package distributedstorage

import (
	"encoding/json"
	"fmt"

	"github.com/quay/config-tool/pkg/lib/shared"
)

type DistributedStorageFieldGroup struct {
	DistributedStorageConfig           map[string]DistributedStorage `default:"{}" validate:"" json:"DISTRIBUTED_STORAGE_CONFIG" yaml:"DISTRIBUTED_STORAGE_CONFIG"`
	DistributedStoragePreference       []string                      `default:"[default]" validate:"" json:"DISTRIBUTED_STORAGE_PREFERENCE" yaml:"DISTRIBUTED_STORAGE_PREFERENCE"`
	DistributedStorageDefaultLocations []string                      `default:"[default]" validate:"" json:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS" yaml:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS"`
	FeatureStorageReplication          bool                          `default:"false" validate:"" json:"FEATURE_STORAGE_REPLICATION" yaml:"FEATURE_STORAGE_REPLICATION"`
}

type DistributedStorage struct {
	Name string                        `default:"" validate:"" json:",inline" yaml:",inline"`
	Args shared.DistributedStorageArgs `default:"" validate:"" json:",inline" yaml:",inline"`
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
