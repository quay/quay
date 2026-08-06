package middleware

import (
	"errors"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

// Prometheus label names used in middleware metric collectors.
const (
	labelOp     = "op"
	labelStatus = "status"
)

// Metrics holds per-instance Prometheus collectors for metastore middleware
// operations. Create one per registry instance via NewMetrics to keep metric
// state isolated between instances.
type Metrics struct {
	registerer prometheus.Registerer
	opDuration *prometheus.HistogramVec
	opTotal    *prometheus.CounterVec
}

// NewMetrics creates and registers middleware metrics with the given
// prometheus.Registerer. Each registry instance should use its own Registerer
// (e.g. prometheus.NewRegistry()) to keep metric state isolated between
// instances. A nil registerer is rejected with an error.
func NewMetrics(reg prometheus.Registerer) (*Metrics, error) {
	if reg == nil {
		return nil, errors.New("middleware: nil prometheus.Registerer")
	}
	m := &Metrics{
		registerer: reg,
		opDuration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name:    "quay_middleware_operation_duration_seconds",
			Help:    "Time spent in metastore operations.",
			Buckets: prometheus.DefBuckets,
		}, []string{labelOp}),
		opTotal: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "quay_middleware_operations_total",
			Help: "Total metastore operations by outcome.",
		}, []string{labelOp, labelStatus}),
	}
	if err := reg.Register(m.opDuration); err != nil {
		return nil, err
	}
	if err := reg.Register(m.opTotal); err != nil {
		reg.Unregister(m.opDuration) // Clean up partial registration.
		return nil, err
	}
	return m, nil
}

// Unregister removes all collectors registered by NewMetrics.
func (m *Metrics) Unregister() {
	if m == nil || m.registerer == nil {
		return
	}
	m.registerer.Unregister(m.opDuration)
	m.registerer.Unregister(m.opTotal)
}

func (m *Metrics) recordOp(op string, start time.Time, err *error) { //nolint:gocritic // ptr needed for defer
	if m == nil {
		return
	}
	m.opDuration.WithLabelValues(op).Observe(time.Since(start).Seconds())
	outcome := "success"
	if *err != nil {
		outcome = "error"
	}
	m.opTotal.WithLabelValues(op, outcome).Inc()
}
