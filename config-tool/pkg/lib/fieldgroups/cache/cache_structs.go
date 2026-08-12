package cache

// CacheFieldGroup represents the cache object Quay will use
type CacheFieldGroup struct {
	DataModelCache *DataModelCacheStruct `default:"" validate:"" json:"DATA_MODEL_CACHE_CONFIG,omitempty" yaml:"DATA_MODEL_CACHE_CONFIG,omitempty"`
}

// DataModelCacheStruct represents the caching settings that Quay will use. Quay supports in-memory cache,
// memcached and Redis.
type DataModelCacheStruct struct {
	Engine                 string           `default:"inmemory" validate:"" json:"engine,omitempty" yaml:"engine,omitempty"`
	Endpoint               []any            `default:"" validate:"" json:"endpoint,omitempty" yaml:"endpoint,omitempty"`
	RepositoryBlobCacheTTL string           `default:"60s" validate:"" json:"repository_blob_cache_ttl,omitempty" yaml:"repository_blob_cache_ttl,omitempty"`
	CatalogPageCacheTTL    string           `default:"60s" validate:"" json:"catalog_page_cache_ttl,omitempty" yaml:"catalog_page_cache_ttl,omitempty"`
	ActiveRepoTagsCacheTTL string           `default:"60s" validate:"" json:"active_repo_tags_cache_ttl,omitempty" yaml:"active_repo_tags_cache_ttl,omitempty"`
	ValueSizeLimit         string           `default:"1MiB" validate:"" json:"value_size_limit,omitempty" yaml:"value_size_limit,omitempty"`
	RedisConfig            RedisConfigGroup `default:"" validate:"" json:"redis_config,omitempty" yaml:"redis_config,omitempty"`
}

// RedisConfigGroup contains fields for both standard Redis and Redis Cluster
type RedisConfigGroup struct {
	// when engine == redis
	Primary *RedisNodeConfig `default:"" validate:"" json:"primary,omitempty" yaml:"primary,omitempty"`
	Replica *RedisNodeConfig `default:"" validate:"" json:"replica,omitempty" yaml:"replica,omitempty"`

	// when engine == rediscluster
	StartupNodes     []RedisNodeConfig `json:"startup_nodes,omitempty" yaml:"startup_nodes,omitempty"`
	ReadFromReplicas bool              `json:"read_from_replicas,omitempty" yaml:"read_from_replicas,omitempty"`
}

// RedisNodeConfig contains the redis nodes
type RedisNodeConfig struct {
	Host     string `json:"host,omitempty" yaml:"host,omitempty"`
	Port     int    `default:"6379" json:"port,omitempty" yaml:"port,omitempty"`
	Password string `json:"password,omitempty" yaml:"password,omitempty"`
	SSL      bool   `default:"false" json:"ssl,omitempty" yaml:"ssl,omitempty"`
}
