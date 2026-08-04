package middleware

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"
	"github.com/prometheus/client_golang/prometheus"
	io_prometheus_client "github.com/prometheus/client_model/go"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/oci"
)

// TestNewMetrics_NilRegisterer verifies that NewMetrics returns an error
// instead of panicking when given a nil Registerer.
func TestNewMetrics_NilRegisterer(t *testing.T) {
	m, err := NewMetrics(nil)
	require.Error(t, err)
	require.Nil(t, m)
	require.ErrorContains(t, err, "nil prometheus.Registerer")
}

// TestNewMetrics_DuplicateRegistration verifies that registering the same
// metric names twice on the same registerer fails cleanly instead of panicking.
func TestNewMetrics_DuplicateRegistration(t *testing.T) {
	reg := prometheus.NewRegistry()
	_, err := NewMetrics(reg)
	require.NoError(t, err)
	_, err = NewMetrics(reg)
	require.Error(t, err, "second NewMetrics on the same registerer must fail")
}

// TestNewMetrics_PartialRegistrationCleanup verifies that if the second
// collector registration fails, the first is unregistered so no partially
// registered state leaks.
func TestNewMetrics_PartialRegistrationCleanup(t *testing.T) {
	reg := prometheus.NewRegistry()

	// Pre-register a conflicting counter with the same name as opTotal.
	conflicting := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "quay_middleware_operations_total",
		Help: "conflicting collector",
	}, []string{labelOp, labelStatus})
	require.NoError(t, reg.Register(conflicting))

	// NewMetrics should fail on the second registration (opTotal).
	_, err := NewMetrics(reg)
	require.Error(t, err)

	// The first collector (opDuration) should have been cleaned up.
	// Verify by successfully re-registering a histogram with the same
	// descriptor (Prometheus keeps a dimHashesByName consistency map that
	// survives Unregister, so name/help/labels must match exactly).
	checkHist := prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "quay_middleware_operation_duration_seconds",
		Help:    "Time spent in metastore operations.",
		Buckets: prometheus.DefBuckets,
	}, []string{"op"})
	require.NoError(t, reg.Register(checkHist), "opDuration should have been unregistered during cleanup")
}

// TestMetrics_NilRecordOp verifies that nil metrics silently skip recording.
func TestMetrics_NilRecordOp(t *testing.T) {
	var m *Metrics
	var retErr error
	require.NotPanics(t, func() {
		m.recordOp("anything", time.Now(), &retErr)
	})
}

// TestMetrics_Isolation verifies that two registry instances with separate
// Prometheus registries record metrics independently—operations on one
// instance do not affect counters visible through the other's registry.
func TestMetrics_Isolation(t *testing.T) {
	regA := prometheus.NewRegistry()
	regB := prometheus.NewRegistry()
	metricsA, err := NewMetrics(regA)
	require.NoError(t, err)
	metricsB, err := NewMetrics(regB)
	require.NoError(t, err)

	storeA := &mockStore{ensureRepoID: 1, putManifestID: 10}
	storeB := &mockStore{ensureRepoID: 2, putManifestID: 20}

	repoA := newRepository(
		&fakeDistRepo{name: namedRef(t), ms: &mockManifestService{putDigest: digest.FromString("a")}},
		storeA, oci.NewBlobLockSet(), "library", metricsA,
	)
	repoB := newRepository(
		&fakeDistRepo{name: namedRef(t), ms: &mockManifestService{putDigest: digest.FromString("b")}},
		storeB, oci.NewBlobLockSet(), "library", metricsB,
	)

	manifest := &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{"schemaVersion":2}`),
	}

	// Put two manifests through instance A, one through B.
	msA, err := repoA.Manifests(context.Background())
	require.NoError(t, err)
	for range 2 {
		_, err = msA.Put(context.Background(), manifest)
		require.NoError(t, err)
	}
	msB, err := repoB.Manifests(context.Background())
	require.NoError(t, err)
	_, err = msB.Put(context.Background(), manifest)
	require.NoError(t, err)

	// Verify A recorded 2 successes, B recorded 1.
	countA := counterValue(t, regA, "quay_middleware_operations_total", "manifest_put", "success")
	countB := counterValue(t, regB, "quay_middleware_operations_total", "manifest_put", "success")
	require.Equal(t, 2.0, countA, "registry A should have 2 manifest_put successes")
	require.Equal(t, 1.0, countB, "registry B should have 1 manifest_put success")

	histA := histogramCount(t, regA, "quay_middleware_operation_duration_seconds", "manifest_put")
	histB := histogramCount(t, regB, "quay_middleware_operation_duration_seconds", "manifest_put")
	require.Equal(t, uint64(2), histA)
	require.Equal(t, uint64(1), histB)
}

// TestMetrics_ErrorOutcome verifies that failed operations record the "error"
// status label.
func TestMetrics_ErrorOutcome(t *testing.T) {
	reg := prometheus.NewRegistry()
	metrics, err := NewMetrics(reg)
	require.NoError(t, err)

	store := &mockStore{ensureRepoID: 1, putManifestErr: errors.New("db locked")}
	repo := newRepository(
		&fakeDistRepo{name: namedRef(t), ms: &mockManifestService{putDigest: digest.FromString("err")}},
		store, oci.NewBlobLockSet(), "library", metrics,
	)
	ms, err := repo.Manifests(context.Background())
	require.NoError(t, err)

	_, err = ms.Put(context.Background(), &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{}`),
	})
	require.Error(t, err)

	errCount := counterValue(t, reg, "quay_middleware_operations_total", "manifest_put", "error")
	require.Equal(t, 1.0, errCount, "error status should be recorded")
}

// TestMetrics_AllOperations verifies that each middleware operation records
// metrics using the per-instance collectors.
func TestMetrics_AllOperations(t *testing.T) {
	reg := prometheus.NewRegistry()
	metrics, err := NewMetrics(reg)
	require.NoError(t, err)

	blobDgst := digest.FromString("blob-content")
	blobDesc := v1.Descriptor{Digest: blobDgst, Size: 42}
	store := &mockStore{ensureRepoID: 1, putManifestID: 1, putBlobID: 1, putTagID: 1}
	innerBW := &mockBlobWriter{commitDesc: blobDesc}

	repo := newRepository(
		&fakeDistRepo{
			name: namedRef(t),
			ms:   &mockManifestService{putDigest: digest.FromString("m")},
			bs:   &mockBlobStore{putDesc: blobDesc, createWr: innerBW},
			ts:   &mockTagService{},
		},
		store, oci.NewBlobLockSet(), "library", metrics,
	)

	ctx := context.Background()
	ms, err := repo.Manifests(ctx)
	require.NoError(t, err)
	_, err = ms.Put(ctx, &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{"schemaVersion":2}`),
	})
	require.NoError(t, err)
	require.NoError(t, ms.Delete(ctx, digest.FromString("d")))

	bs := repo.Blobs(ctx)
	_, err = bs.Put(ctx, "application/octet-stream", []byte("blob-content"))
	require.NoError(t, err)
	wr, err := bs.Create(ctx)
	require.NoError(t, err)
	_, err = wr.Commit(ctx, blobDesc)
	require.NoError(t, err)

	ts := repo.Tags(ctx)
	require.NoError(t, ts.Tag(ctx, "v1", v1.Descriptor{Digest: digest.FromString("t")}))
	require.NoError(t, ts.Untag(ctx, "old"))

	for _, op := range []string{"manifest_put", "manifest_delete", "blob_put", "blob_create", "blob_commit", "tag", "untag"} {
		count := counterValue(t, reg, "quay_middleware_operations_total", op, "success")
		require.Equal(t, 1.0, count, "expected 1 success for %s", op)
	}
}

// TestMetrics_ConcurrentConstruction verifies that creating metrics on
// separate registries concurrently is safe.
func TestMetrics_ConcurrentConstruction(t *testing.T) {
	const goroutines = 20
	var wg sync.WaitGroup
	errs := make(chan error, goroutines)
	for range goroutines {
		wg.Add(1)
		go func() {
			defer wg.Done()
			reg := prometheus.NewRegistry()
			_, err := NewMetrics(reg)
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		require.NoError(t, err)
	}
}

// --- test helpers ---

// counterValue gathers metrics from a registry and returns the counter value
// for the metric with the given name and label values (op, status).
func counterValue(t *testing.T, reg *prometheus.Registry, name, op, status string) float64 { //nolint:unparam // name kept generic for reuse
	t.Helper()
	families, err := reg.Gather()
	require.NoError(t, err)
	for _, fam := range families {
		if fam.GetName() != name {
			continue
		}
		for _, m := range fam.GetMetric() {
			if matchLabels(m.GetLabel(), map[string]string{"op": op, "status": status}) {
				return m.GetCounter().GetValue()
			}
		}
	}
	t.Fatalf("metric %s{op=%q,status=%q} not found", name, op, status)
	return 0
}

// histogramCount returns the sample count for a histogram metric.
func histogramCount(t *testing.T, reg *prometheus.Registry, name, op string) uint64 {
	t.Helper()
	families, err := reg.Gather()
	require.NoError(t, err)
	for _, fam := range families {
		if fam.GetName() != name {
			continue
		}
		for _, m := range fam.GetMetric() {
			if matchLabels(m.GetLabel(), map[string]string{"op": op}) {
				return m.GetHistogram().GetSampleCount()
			}
		}
	}
	t.Fatalf("metric %s{op=%q} not found", name, op)
	return 0
}

func matchLabels(pairs []*io_prometheus_client.LabelPair, want map[string]string) bool {
	if len(pairs) < len(want) {
		return false
	}
	for k, v := range want {
		found := false
		for _, p := range pairs {
			if p.GetName() == k && p.GetValue() == v {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}
