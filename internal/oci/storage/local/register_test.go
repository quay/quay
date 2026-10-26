package local

import (
	"testing"

	"github.com/distribution/distribution/v3/registry/storage/driver/base"
	"github.com/distribution/distribution/v3/registry/storage/driver/factory"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/oci"
)

type metadataStoreStub struct {
	oci.MetadataStore
}

func TestQuayDriverFactoryRejectsInvalidMetastore(t *testing.T) {
	for _, params := range []map[string]interface{}{
		{
			rootDirectoryParameter: t.TempDir(),
		},
		{
			rootDirectoryParameter: t.TempDir(),
			metastoreParameter:     "not a metastore",
		},
	} {
		_, err := (&quayDriverFactory{}).Create(t.Context(), params)
		require.ErrorContains(t, err, "metastore parameter must implement oci.MetadataStore")
	}
}

func TestQuayDriverFactoryUsesStoreParameter(t *testing.T) {
	Register()

	firstStore := &metadataStoreStub{}
	secondStore := &metadataStoreStub{}

	first := createDistDriver(t, firstStore)
	second := createDistDriver(t, secondStore)

	require.Same(t, firstStore, first.meta)
	require.Same(t, secondStore, second.meta)
}

func createDistDriver(t *testing.T, store oci.MetadataStore) *DistDriver {
	t.Helper()

	driver, err := factory.Create(t.Context(), Name(), Parameters(t.TempDir(), store))
	require.NoError(t, err)

	baseDriver, ok := driver.(*base.Base)
	require.True(t, ok)
	distDriver, ok := baseDriver.StorageDriver.(*DistDriver)
	require.True(t, ok)
	return distDriver
}
