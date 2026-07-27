package local

import (
	"context"
	"fmt"
	"sync"

	"github.com/distribution/distribution/v3/configuration"
	storagedriver "github.com/distribution/distribution/v3/registry/storage/driver"
	"github.com/distribution/distribution/v3/registry/storage/driver/base"
	"github.com/distribution/distribution/v3/registry/storage/driver/factory"

	"github.com/quay/quay/internal/oci"
)

const (
	driverName             = "quay"
	rootDirectoryParameter = "rootdirectory"
	metastoreParameter     = "metastore"
)

var registerFactory = sync.OnceFunc(func() {
	factory.Register(driverName, &quayDriverFactory{})
})

// Register makes the stateless Quay storage factory available to distribution.
// It is safe to call multiple times and concurrently.
func Register() {
	registerFactory()
}

// Name returns the name used to register the storage driver with distribution.
func Name() string { return driverName }

// Parameters builds distribution parameters for the local Quay driver.
func Parameters(rootDir string, meta oci.MetadataStore) configuration.Parameters {
	return configuration.Parameters{
		rootDirectoryParameter: rootDir,
		metastoreParameter:     meta,
	}
}

type quayDriverFactory struct{}

func (f *quayDriverFactory) Create(ctx context.Context, params map[string]interface{}) (storagedriver.StorageDriver, error) {
	rootDir, ok := params[rootDirectoryParameter].(string)
	if !ok || rootDir == "" {
		return nil, fmt.Errorf("quay storage driver: rootdirectory parameter required")
	}
	meta, ok := params[metastoreParameter].(oci.MetadataStore)
	if !ok || meta == nil {
		return nil, fmt.Errorf("quay storage driver: metastore parameter must implement oci.MetadataStore")
	}
	blobs, err := New(rootDir)
	if err != nil {
		return nil, err
	}
	return &base.Base{StorageDriver: NewDistDriver(blobs, meta)}, nil
}
