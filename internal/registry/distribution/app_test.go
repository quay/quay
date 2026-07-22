package distribution

import (
	"strings"
	"testing"

	"github.com/distribution/distribution/v3/registry/handlers"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/oci"
)

type metadataStoreStub struct {
	oci.MetadataStore
}

type registryTokenServiceStub struct {
	registryTokenService
}

func TestNewRegistryRejectsNilBlobLocker(t *testing.T) {
	_, err := NewRegistry(t.Context(), &Config{})
	if err == nil {
		t.Fatal("expected missing blob locker to be rejected")
	}
	if !strings.Contains(err.Error(), "nil blob locker") {
		t.Fatalf("expected nil blob locker error, got %v", err)
	}
}

func TestNewRegistryPassesStoreToDistributionDriver(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	store := &metadataStoreStub{}

	registry, err := NewRegistry(t.Context(), &Config{
		StoragePath: t.TempDir(),
		Hostname:    "registry.example.com",
		TokenRealm:  "https://registry.example.com/v2/auth",
		DB:          db,
		Store:       store,
		BlobLocker:  oci.NewBlobLockSet(),
		JWTService:  &registryTokenServiceStub{},
	})
	require.NoError(t, err)

	app, ok := registry.Handler().(*handlers.App)
	require.True(t, ok)
	require.Same(t, store, app.Config.Storage.Parameters()["metastore"])
}
