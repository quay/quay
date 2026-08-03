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
	locker := oci.NewBlobLockSet()

	registry, err := NewRegistry(t.Context(), &Config{
		StoragePath: t.TempDir(),
		Hostname:    "registry.example.com",
		TokenRealm:  "https://registry.example.com/v2/auth",
		DB:          db,
		Store:       store,
		BlobLocker:  locker,
		JWTService:  &registryTokenServiceStub{},
	})
	require.NoError(t, err)

	app, ok := registry.Handler().(*handlers.App)
	require.True(t, ok)
	require.Same(t, store, app.Config.Storage.Parameters()["metastore"])

	middleware := app.Config.Middleware[repositoryResourceType]
	require.Len(t, middleware, 1)
	require.Same(t, store, middleware[0].Options["metastore"])
	require.Same(t, locker, middleware[0].Options["bloblocker"])
	require.Equal(t, defaultLibraryNamespace, middleware[0].Options["librarynamespace"])
}

func TestNewRegistryKeepsMiddlewareOptionsPerInstance(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	jwt := &registryTokenServiceStub{}
	storeA := &metadataStoreStub{}
	storeB := &metadataStoreStub{}
	lockerA := oci.NewBlobLockSet()
	lockerB := oci.NewBlobLockSet()

	registryA, err := NewRegistry(t.Context(), &Config{
		StoragePath:      t.TempDir(),
		Hostname:         "registry-a.example.com",
		TokenRealm:       "https://registry-a.example.com/v2/auth",
		DB:               db,
		Store:            storeA,
		BlobLocker:       lockerA,
		LibraryNamespace: "library-a",
		JWTService:       jwt,
	})
	require.NoError(t, err)
	registryB, err := NewRegistry(t.Context(), &Config{
		StoragePath:      t.TempDir(),
		Hostname:         "registry-b.example.com",
		TokenRealm:       "https://registry-b.example.com/v2/auth",
		DB:               db,
		Store:            storeB,
		BlobLocker:       lockerB,
		LibraryNamespace: "library-b",
		JWTService:       jwt,
	})
	require.NoError(t, err)

	appA, ok := registryA.Handler().(*handlers.App)
	require.True(t, ok)
	appB, ok := registryB.Handler().(*handlers.App)
	require.True(t, ok)
	optionsA := appA.Config.Middleware[repositoryResourceType][0].Options
	optionsB := appB.Config.Middleware[repositoryResourceType][0].Options
	require.Same(t, storeA, optionsA["metastore"])
	require.Same(t, lockerA, optionsA["bloblocker"])
	require.Equal(t, "library-a", optionsA["librarynamespace"])
	require.Same(t, storeB, optionsB["metastore"])
	require.Same(t, lockerB, optionsB["bloblocker"])
	require.Equal(t, "library-b", optionsB["librarynamespace"])
}
