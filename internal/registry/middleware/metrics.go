package middleware

import (
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	opDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "quay_middleware_operation_duration_seconds",
		Help:    "Time spent in metastore operations.",
		Buckets: prometheus.DefBuckets,
	}, []string{"op"})

	opTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "quay_middleware_operations_total",
		Help: "Total metastore operations by outcome.",
	}, []string{"op", "status"})
)

func recordOp(op string, start time.Time, err *error) { //nolint:gocritic // ptr needed for defer
	opDuration.WithLabelValues(op).Observe(time.Since(start).Seconds())
	status := "success"
	if *err != nil {
		status = "error"
	}
	opTotal.WithLabelValues(op, status).Inc()
}
