package local

import (
	"context"
	"fmt"
	"sync"

	storagedriver "github.com/distribution/distribution/v3/registry/storage/driver"
	"github.com/distribution/distribution/v3/registry/storage/driver/base"
	"github.com/distribution/distribution/v3/registry/storage/driver/factory"

	"github.com/quay/quay/internal/oci"
)

var (
	metaMu         sync.RWMutex
	registeredMeta oci.MetadataStore
)

// RegisterMetadataStore sets the MetadataStore used when the factory creates
// a DistDriver. Must be called before distribution creates the storage driver.
func RegisterMetadataStore(meta oci.MetadataStore) {
	if meta == nil {
		panic("RegisterMetadataStore called with nil")
	}
	metaMu.Lock()
	registeredMeta = meta
	metaMu.Unlock()
}

func init() {
	factory.Register("quay", &quayDriverFactory{})
}

type quayDriverFactory struct{}

func (f *quayDriverFactory) Create(ctx context.Context, params map[string]interface{}) (storagedriver.StorageDriver, error) {
	rootDir, ok := params["rootdirectory"].(string)
	if !ok || rootDir == "" {
		return nil, fmt.Errorf("quay storage driver: rootdirectory parameter required")
	}
	metaMu.RLock()
	meta := registeredMeta
	metaMu.RUnlock()
	if meta == nil {
		return nil, fmt.Errorf("quay storage driver: metastore not registered (call RegisterMetadataStore first)")
	}
	blobs, err := New(rootDir)
	if err != nil {
		return nil, err
	}
	return &base.Base{StorageDriver: NewDistDriver(blobs, meta)}, nil
}
