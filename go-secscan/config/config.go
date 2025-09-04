package config

import (
	"time"
)

// Config holds service configuration values.
type Config struct {
	Addr                 string
	JWTPSK               string
	IndexMaxLayerSize    string
	ReindexThreshold     time.Duration
	IndexerState         string
	NotificationPageSize int

	IndexingIntervalSeconds       int
	V4BatchSize                   int
	RecentManifestBatchSize       int
	EnableIndexingLock            bool
	EnableRecentManifestBatchLock bool
	ReindexThresholdSeconds       int
}
