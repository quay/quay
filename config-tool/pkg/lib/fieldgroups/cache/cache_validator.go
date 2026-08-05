package cache

import (
	"crypto/tls"
	"net"
	"strconv"

	"github.com/go-redis/redis/v8"
	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for the cache field group.
func (fg *CacheFieldGroup) Validate(opts shared.Options) []shared.ValidationError {
	errors := []shared.ValidationError{}
	const fgName = "Cache"

	// cache configuration is optional, if it's missing just return
	if fg.DataModelCache == nil {
		return errors
	}

	// validate engines
	validateEngines := []string{"inmemory", "memcached", "redis", "rediscluster"}
	if ok, err := shared.ValidateIsOneOfString(fg.DataModelCache.Engine, validateEngines,
		"DATA_MODEL_CACHE_CONFIG.engine", fgName); !ok {
		errors = append(errors, err)
		return errors
	}

	// validate TTL fields are set
	if fg.DataModelCache.RepositoryBlobCacheTTL != "" {
		if ok, err := shared.ValidateTimePattern(fg.DataModelCache.RepositoryBlobCacheTTL,
			"DATA_MODEL_CACHE_CONFIG.repository_blob_cache_ttl", fgName); !ok {
			errors = append(errors, err)
		}
	}

	if fg.DataModelCache.ActiveRepoTagsCacheTTL != "" {
		if ok, err := shared.ValidateTimePattern(fg.DataModelCache.ActiveRepoTagsCacheTTL,
			"DATA_MODEL_CACHE_CONFIG.active_repo_tags_cache_ttl", fgName); !ok {
			errors = append(errors, err)
		}
	}

	if fg.DataModelCache.CatalogPageCacheTTL != "" {
		if ok, err := shared.ValidateTimePattern(fg.DataModelCache.CatalogPageCacheTTL,
			"DATA_MODEL_CACHE_CONFIG.catalog_page_cache_ttl", fgName); !ok {
			errors = append(errors, err)
		}
	}

	// validate that the cache size is properly set
	if fg.DataModelCache.ValueSizeLimit != "" {
		if ok, err := shared.ValidateCacheSizePattern(fg.DataModelCache.ValueSizeLimit,
			"DATA_MODEL_CACHE_CONFIG.value_size_limit", fgName); !ok {
			errors = append(errors, err)
		}
	}

	// only run if we are not in "testing" mode because we cannot confirm that these instances will be available
	if opts.Mode != "testing" {
		switch fg.DataModelCache.Engine {
		// validate that memcached instance is available if defined
		case "memcached":
			if ok, err := shared.ValidateMemcachedInstance(fg.DataModelCache.Endpoint[0].(string),
				fg.DataModelCache.Endpoint[1].(int), "DATA_MODEL_CACHE_CONFIG.endpoint", fgName); !ok {
				errors = append(errors, err)
			}

		// validate that redis primary instance is available
		case "redis":
			var tlsConfig *tls.Config = nil
			if fg.DataModelCache.RedisConfig.Primary.SSL {
				tlsConfig = &tls.Config{
					InsecureSkipVerify: false,
				}
			}

			options := &redis.Options{
				Addr: net.JoinHostPort(fg.DataModelCache.RedisConfig.Primary.Host,
					strconv.Itoa(fg.DataModelCache.RedisConfig.Primary.Port)),
				Password:  fg.DataModelCache.RedisConfig.Primary.Pass,
				DB:        0,
				TLSConfig: tlsConfig,
			}

			if ok, err := shared.ValidateRedisConnection(options,
				"DATA_MODEL_CACHE_CONFIG.redis_config.primary.host", fgName); !ok {
				errors = append(errors, err)
			}

			// check if there is a secondary redis instance
			if fg.DataModelCache.RedisConfig.Replica != nil {
				var tlsConfig *tls.Config = nil
				if fg.DataModelCache.RedisConfig.Replica.SSL {
					tlsConfig = &tls.Config{
						InsecureSkipVerify: false,
					}
				}

				options := &redis.Options{
					Addr: net.JoinHostPort(fg.DataModelCache.RedisConfig.Replica.Host,
						strconv.Itoa(fg.DataModelCache.RedisConfig.Replica.Port)),
					Password:  fg.DataModelCache.RedisConfig.Replica.Pass,
					DB:        0,
					TLSConfig: tlsConfig,
				}

				if ok, err := shared.ValidateRedisConnection(options,
					"DATA_MODEL_CACHE_CONFIG.redis_config.replica.host", fgName); !ok {
					errors = append(errors, err)
				}
			}

		case "rediscluster":
			// we need to verify that all defined startup nodes are available
			for _, node := range fg.DataModelCache.RedisConfig.StartupNodes {
				var tlsConfig *tls.Config = nil
				if node.SSL {
					tlsConfig = &tls.Config{
						InsecureSkipVerify: false,
					}
				}

				options := &redis.Options{
					Addr:      net.JoinHostPort(node.Host, strconv.Itoa(node.Port)),
					Password:  node.Pass,
					DB:        0,
					TLSConfig: tlsConfig,
				}

				if ok, err := shared.ValidateRedisConnection(options,
					"DATA_MODEL_CACHE_CONFIG.redis_config.startup_nodes.host", fgName); !ok {
					errors = append(errors, err)
				}
			}
		}
	}
	return errors
}
