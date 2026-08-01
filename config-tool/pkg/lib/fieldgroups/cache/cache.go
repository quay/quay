package cache

import (
	"encoding/json"
	"errors"
	"fmt"

	"github.com/creasty/defaults"
)

// NewDataModelCacheStructGroup creates and validates the new cache group and returns it to the caller.
// Raises an error if validation fails.
func NewDataModelCacheStructGroup(fullConfig map[string]any) (*DataModelCacheStruct, error) {
	cacheStruct := &DataModelCacheStruct{}
	defaults.Set(cacheStruct)

	if value, ok := fullConfig["engine"]; ok {
		cacheStruct.Engine, ok = value.(string)
		if !ok {
			return cacheStruct, errors.New("engine must be of type string")
		}

		// fail if the caching engine is unsupported
		if !(cacheStruct.Engine == "memcached" || cacheStruct.Engine == "inmemory" || cacheStruct.Engine == "redis" ||
			cacheStruct.Engine == "rediscluster") {
			return cacheStruct, errors.New("unsupported caching model: must be inmemory, redis, memcached or rediscluster")
		}
	}

	// if engine is memcached but we don't have an endpoint, exit
	if cacheStruct.Engine == "memcached" {
		if _, ok := fullConfig["endpoint"]; !ok {
			return cacheStruct, errors.New("wrong configuration: caching engine is memcached, but endpoint is missing")
		}
	}

	if value, ok := fullConfig["endpoint"]; ok {
		if cacheStruct.Engine != "memcached" {
			return cacheStruct, errors.New("wrong configuration: endpoint is only used for memcached model")
		}

		endpointSlice, isSlice := value.([]any)
		if !isSlice {
			return cacheStruct, errors.New("wrong configuration: endpoint must be an array/slice")
		}

		if len(endpointSlice) != 2 {
			return cacheStruct, errors.New("wrong configuration: endpoint should only contain hostname and port")
		}

		// verify hostname
		_, ok := endpointSlice[0].(string)
		if !ok {
			return cacheStruct, errors.New("wrong configuration: host (first element) must be a string")
		}

		// verify port number and also check the type of the variable so it can be properly stored
		var port int
		switch v := endpointSlice[1].(type) {
		case int:
			port = v
		case float64:
			port = int(v)
		default:
			return cacheStruct, errors.New("wrong configuration: port must be a number")
		}

		if port < 1 || port > 65535 {
			return cacheStruct, errors.New("wrong configuration: port must be in the range 1-65535")
		}

		cacheStruct.Endpoint = []any{endpointSlice[0], port}
	}

	if value, ok := fullConfig["repository_blob_cache_ttl"]; ok {
		cacheStruct.RepositoryBlobCacheTTL, ok = value.(string)
		if !ok {
			return cacheStruct,
				errors.New("wrong configuration: repository_blob_cache_ttl must be a time string, for example '60s'")
		}
	}

	if value, ok := fullConfig["active_repo_tags_cache_ttl"]; ok {
		cacheStruct.ActiveRepoTagsCacheTTL, ok = value.(string)
		if !ok {
			return cacheStruct,
				errors.New("wrong configuration: active_repo_tags_cache_ttl must be a time string, for example '60s'")
		}
	}

	if value, ok := fullConfig["catalog_page_cache_ttl"]; ok {
		cacheStruct.CatalogPageCacheTTL, ok = value.(string)
		if !ok {
			return cacheStruct,
				errors.New("wrong configuration: catalog_page_cache_ttl must be a time string, for example '60s'")
		}
	}

	if value, ok := fullConfig["value_size_limit"]; ok {
		cacheStruct.ValueSizeLimit, ok = value.(string)
		if !ok {
			return cacheStruct,
				errors.New("wrong configuration: value_size_limit must be a string, for instance '1MiB'")
		}
	}

	// if the engine is redis or rediscluster, check that we have a redis_config in place
	if cacheStruct.Engine == "redis" || cacheStruct.Engine == "rediscluster" {
		if _, ok := fullConfig["redis_config"]; !ok {
			return cacheStruct, errors.New("wrong configuration: Engine set to Redis but config is missing redis_config fields")
		}
	}

	if value, ok := fullConfig["redis_config"]; ok {
		if cacheStruct.Engine != "redis" && cacheStruct.Engine != "rediscluster" {
			errString := fmt.Sprintf("wrong configuration: redis_config is present, but engine is %s", cacheStruct.Engine)
			return cacheStruct, errors.New(errString)
		}

		// temporaily marshal the value into JSON so we can properly store it
		jsonBytes, err := json.Marshal(value)
		if err != nil {
			return cacheStruct, errors.New("wrong configuration: invalid redis_config format")
		}

		var redisConfig RedisConfigGroup
		if err := json.Unmarshal(jsonBytes, &redisConfig); err != nil {
			return cacheStruct, errors.New("wrong configuration: cannot parse redis_config")
		}

		// set defaults for the redisConfig
		defaults.Set(&redisConfig)

		// if engine is redis then we need to check if we have a primary (and potentially a replica) key present
		if cacheStruct.Engine == "redis" {
			if redisConfig.Primary == nil {
				return cacheStruct, errors.New("wrong configuration: primary redis caching instance undefined")
			}

			// check that primary key contains host and port and they are not empty
			if redisConfig.Primary.Host == "" {
				return cacheStruct, errors.New("wrong configuration: no host found for primary redis instance")
			}

			if redisConfig.Primary.Port < 1 || redisConfig.Primary.Port > 65535 {
				return cacheStruct, errors.New("wrong configuration: port number for primary instance must be in range 1-65535")
			}
			// if replica is defined, check host and port numbers, if not defined, don't fail
			if redisConfig.Replica != nil {
				// check that primary key contains host and port and they are not empty
				if redisConfig.Replica.Host == "" {
					return cacheStruct, errors.New("wrong configuration: no host found for replica redis instance")
				}

				if redisConfig.Replica.Port < 1 || redisConfig.Replica.Port > 65535 {
					return cacheStruct, errors.New("wrong configuration: port number for replica instance must be in range 1-65535")
				}
			}
			cacheStruct.RedisConfig.Primary = redisConfig.Primary
			cacheStruct.RedisConfig.Replica = redisConfig.Replica
		}

		// if engine is rediscluster
		if cacheStruct.Engine == "rediscluster" {
			if len(redisConfig.StartupNodes) == 0 {
				return cacheStruct, errors.New("wrong configuration: rediscluster requires a list of startup nodes to be present")
			}

			// for each startup node check that host and port are properly defined
			for _, node := range redisConfig.StartupNodes {
				if node.Host == "" {
					return cacheStruct, errors.New("wrong configuration: each startup_node entry must have a hostname")
				}

				if node.Port < 1 || node.Port > 65535 {
					return cacheStruct, errors.New("wrong configuration: startup_node port must be in range 1-65535")
				}
			}
			cacheStruct.RedisConfig = redisConfig
		}
	}

	return cacheStruct, nil
}

// NewCacheFieldGroup creates a new cache field group.
func NewCacheFieldGroup(fullConfig map[string]any) (*CacheFieldGroup, error) {
	newCacheFieldGroup := &CacheFieldGroup{}
	defaults.Set(newCacheFieldGroup)

	if value, ok := fullConfig["DATA_MODEL_CACHE_CONFIG"]; ok {
		var err error
		configMap, isMap := value.(map[string]any)
		if !isMap {
			return newCacheFieldGroup, errors.New("DATA_MODEL_CACHE_CONFIG must be a configuration map/block")
		}

		newCacheFieldGroup.DataModelCache, err = NewDataModelCacheStructGroup(configMap)
		if err != nil {
			return newCacheFieldGroup, err
		}
	}
	return newCacheFieldGroup, nil
}
