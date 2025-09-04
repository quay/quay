package main

import (
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/quay/go-secscan/config"
	"github.com/quay/go-secscan/internal/clairv4"
)

func mustGetenv(k, def string) string {
	v := os.Getenv(k)
	if v == "" {
		return def
	}
	return v
}

func mustGetenvInt(k string, def int) int {
	v := os.Getenv(k)
	if v == "" {
		return def
	}
	i, err := strconv.Atoi(v)
	if err != nil {
		return def
	}
	return i
}

func loadConfig() config.Config {
	return config.Config{
		Addr:                          mustGetenv("SECURITY_SCANNER_ADDR", ":8080"),
		JWTPSK:                        mustGetenv("SECURITY_SCANNER_V4_PSK", ""),
		IndexMaxLayerSize:             mustGetenv("SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE", ""),
		IndexerState:                  mustGetenv("SECURITY_SCANNER_V4_INDEXER_STATE", "abc"),
		NotificationPageSize:          mustGetenvInt("SECURITY_SCANNER_V4_NOTIFICATION_PAGE_SIZE", 0),
		IndexingIntervalSeconds:       mustGetenvInt("SECURITY_SCANNER_INDEXING_INTERVAL", 30),
		V4BatchSize:                   mustGetenvInt("SECURITY_SCANNER_V4_BATCH_SIZE", 0),
		RecentManifestBatchSize:       mustGetenvInt("SECURITY_SCANNER_V4_RECENT_MANIFEST_BATCH_SIZE", 1000),
		EnableIndexingLock:            mustGetenvInt("SECURITY_SCANNER_V4_LOCK", 0) == 1,
		EnableRecentManifestBatchLock: mustGetenvInt("SECURITY_SCANNER_V4_RECENT_MANIFEST_BATCH_LOCK", 0) == 1,
		ReindexThresholdSeconds:       mustGetenvInt("SECURITY_SCANNER_V4_REINDEX_THRESHOLD", 86400),
	}
}

func main() {
	cfg := loadConfig()
	endpoint := mustGetenv("SECURITY_SCANNER_V4_ENDPOINT", "http://localhost:6060")
	client, err := clairv4.New(endpoint, &http.Client{}, cfg.JWTPSK)
	if err != nil {
		log.Fatal(err)
	}
	client = client.WithMaxLayerSize(cfg.IndexMaxLayerSize)

	interval := time.Duration(cfg.IndexingIntervalSeconds) * time.Second
	log.Printf("starting worker; interval=%s", interval)
	for {
		state, err := client.State()
		if err != nil {
			log.Printf("error retrieving indexer state: %v", err)
		} else {
			log.Printf("indexer state: %v", state)
		}
		time.Sleep(interval)
	}
}
