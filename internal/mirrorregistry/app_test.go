package mirrorregistry

import (
	"context"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"sync"
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	dto "github.com/prometheus/client_model/go"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/bootstrap"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
)

func testConfig(t *testing.T) *Config {
	t.Helper()
	dataDir := t.TempDir()
	storagePath := filepath.Join(dataDir, "storage")
	resolved := &config.Resolved{
		Config:      config.NewDefault("localhost:8443", storagePath),
		DataDir:     dataDir,
		StoragePath: storagePath,
		DBPath:      filepath.Join(dataDir, "quay.db"),
	}
	resolved.Config.PreferredURLScheme = "http"

	db, err := dbcore.Setup(t.Context(), resolved.DBPath)
	require.NoError(t, err)
	_, err = bootstrap.AdminUser(t.Context(), db, "admin", "password")
	require.NoError(t, err)
	require.NoError(t, db.Close())

	return &Config{
		Resolved:   resolved,
		Features:   resolved.Config.Features,
		ListenAddr: "127.0.0.1:0",
	}
}

func TestNewAssemblesTopLevelRoutes(t *testing.T) {
	app, err := New(t.Context(), testConfig(t))
	require.NoError(t, err)
	defer func() { require.NoError(t, app.Close()) }()

	tests := []struct {
		path   string
		method string
		want   int
	}{
		{path: "/healthz", method: http.MethodGet, want: http.StatusOK},
		{path: "/metrics", method: http.MethodGet, want: http.StatusOK},
		{path: "/v2/", method: http.MethodGet, want: http.StatusUnauthorized},
		{path: "/v2/auth", method: http.MethodGet, want: http.StatusUnauthorized},
		{path: "/api/v1/repository/library/test", method: http.MethodDelete, want: http.StatusUnauthorized},
	}
	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			req := httptest.NewRequestWithContext(t.Context(), tt.method, tt.path, http.NoBody)
			resp := httptest.NewRecorder()
			app.Handler().ServeHTTP(resp, req)
			assert.Equal(t, tt.want, resp.Code)
		})
	}
}

func TestNewUsesIndependentDefaultMetricsRegistries(t *testing.T) {
	var configs [2]*Config
	for i := range configs {
		configs[i] = testConfig(t)
	}

	apps := make([]*App, len(configs))
	errs := make(chan error, len(configs))
	var wg sync.WaitGroup
	for i := range configs {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			app, err := New(context.Background(), configs[i])
			apps[i] = app
			errs <- err
		}(i)
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		require.NoError(t, err)
	}
	for _, app := range apps {
		require.NotNil(t, app)
		resp := httptest.NewRecorder()
		app.Handler().ServeHTTP(resp, httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/metrics", http.NoBody))
		require.Equal(t, http.StatusOK, resp.Code)
		require.NoError(t, app.Close())
	}
}

func TestNewUsesExplicitMetricsDependencies(t *testing.T) {
	registry := prometheus.NewRegistry()
	cfg := testConfig(t)
	cfg.MetricsRegisterer = registry
	cfg.MetricsGatherer = registry

	app, err := New(t.Context(), cfg)
	require.NoError(t, err)
	defer func() { require.NoError(t, app.Close()) }()

	resp := httptest.NewRecorder()
	app.Handler().ServeHTTP(resp, httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/metrics", http.NoBody))
	require.Equal(t, http.StatusOK, resp.Code)
	families, err := registry.Gather()
	require.NoError(t, err)
	assert.Contains(t, metricNames(families), "promhttp_metric_handler_requests_total")
}

func TestNewRejectsPartialMetricsDependencies(t *testing.T) {
	cfg := testConfig(t)
	cfg.MetricsRegisterer = prometheus.NewRegistry()
	_, err := New(t.Context(), cfg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "provided together")
}

func TestNewDoesNotMutateCallerConfiguration(t *testing.T) {
	cfg := testConfig(t)
	cfg.Resolved.Config.SuperUsers = []string{"caller-configured-user"}
	cfg.Resolved.Config.RobotsWhitelist = []string{"caller-configured-robot"}
	superUsersBefore := append([]string(nil), cfg.Resolved.Config.SuperUsers...)
	robotsBefore := append([]string(nil), cfg.Resolved.Config.RobotsWhitelist...)

	app, err := New(t.Context(), cfg)
	require.NoError(t, err)
	require.NoError(t, app.Close())

	assert.Equal(t, superUsersBefore, cfg.Resolved.Config.SuperUsers)
	assert.Equal(t, robotsBefore, cfg.Resolved.Config.RobotsWhitelist)
}

func TestConfigureStandaloneSuperuser(t *testing.T) {
	t.Run("defaults follow initialized user", func(t *testing.T) {
		resolved := &config.Resolved{Config: config.NewDefault("localhost", "/data/storage")}

		configureStandaloneSuperuser(resolved, "custom-admin")

		assert.Equal(t, []string{"custom-admin"}, resolved.Config.SuperUsers)
	})

	t.Run("explicit config remains authoritative", func(t *testing.T) {
		resolved := &config.Resolved{
			Config:   config.NewDefault("localhost", "/data/storage"),
			FromFile: true,
		}
		resolved.Config.SuperUsers = []string{"configured-admin"}

		configureStandaloneSuperuser(resolved, "database-user")

		assert.Equal(t, []string{"configured-admin"}, resolved.Config.SuperUsers)
	})
}

func TestCloseStopsGCAndIsIdempotent(t *testing.T) {
	app, err := New(t.Context(), testConfig(t))
	require.NoError(t, err)
	require.NotNil(t, app.workerDone)

	require.NoError(t, app.Close())
	select {
	case <-app.workerDone:
	default:
		t.Fatal("Close returned before the GC worker stopped")
	}
	require.NoError(t, app.Close())
	assert.Nil(t, (*App)(nil).Close())
}

func TestNewCleansUpPartialConstruction(t *testing.T) {
	cfg := testConfig(t)
	cfg.Resolved.Config.ServerHostname = ""

	_, err := New(t.Context(), cfg)
	require.Error(t, err)

	db, err := dbcore.Setup(t.Context(), cfg.Resolved.DBPath)
	require.NoError(t, err)
	require.NoError(t, db.Close())
}

func metricNames(families []*dto.MetricFamily) []string {
	result := make([]string, 0, len(families))
	for _, family := range families {
		result = append(result, family.GetName())
	}
	return result
}
