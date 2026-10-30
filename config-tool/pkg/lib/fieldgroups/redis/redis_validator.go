package redis

import (
	"crypto/tls"
	"fmt"

	"github.com/go-redis/redis/v8"
	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *RedisFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	errors := []shared.ValidationError{}

	// Check for build logs config
	if ok, err := shared.ValidateRequiredObject(fg.BuildlogsRedis, "BUILDLOGS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
		return errors
	}

	// Check for build log host
	if ok, err := shared.ValidateRequiredString(fg.BuildlogsRedis.Host, "BUILDLOGS_REDIS.HOST", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Check for user events config
	if ok, err := shared.ValidateRequiredObject(fg.UserEventsRedis, "USER_EVENTS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
		return errors
	}

	// When engine is rediscluster, host is used only for the Go config-tool
	// standalone validation fallback; the Python side uses redis_config.startup_nodes.
	// Accept the config as valid if either host is set or startup_nodes are provided.
	if fg.UserEventsRedis.Engine != "rediscluster" {
		if ok, err := shared.ValidateRequiredString(fg.UserEventsRedis.Host, "USER_EVENTS_REDIS.HOST", "Redis"); !ok {
			errors = append(errors, err)
		}
	} else if fg.UserEventsRedis.Host == "" && (fg.UserEventsRedis.RedisConfig == nil || len(fg.UserEventsRedis.RedisConfig.StartupNodes) == 0) {
		newError := shared.ValidationError{
			Tags:       []string{"USER_EVENTS_REDIS"},
			FieldGroup: "Redis",
			Message:    "USER_EVENTS_REDIS with engine 'rediscluster' requires either host or redis_config.startup_nodes",
		}
		errors = append(errors, newError)
	}

	// Check for pull metrics config (only if provided)
	if fg.PullMetricsRedis != nil {
		if fg.PullMetricsRedis.Engine != "rediscluster" {
			if ok, err := shared.ValidateRequiredString(fg.PullMetricsRedis.Host, "PULL_METRICS_REDIS.HOST", "Redis"); !ok {
				errors = append(errors, err)
			}
		} else if fg.PullMetricsRedis.Host == "" && (fg.PullMetricsRedis.RedisConfig == nil || len(fg.PullMetricsRedis.RedisConfig.StartupNodes) == 0) {
			newError := shared.ValidationError{
				Tags:       []string{"PULL_METRICS_REDIS"},
				FieldGroup: "Redis",
				Message:    "PULL_METRICS_REDIS with engine 'rediscluster' requires either host or redis_config.startup_nodes",
			}
			errors = append(errors, newError)
		}
	}

	// Validate BUILDLOGS_REDIS connection (always standalone)
	addr := fg.BuildlogsRedis.Host
	if fg.BuildlogsRedis.Port != 0 {
		addr = addr + ":" + fmt.Sprintf("%d", fg.BuildlogsRedis.Port)
	}

	var tlsConfig *tls.Config = nil
	if fg.BuildlogsRedis.Ssl {
		tlsConfig = &tls.Config{
			InsecureSkipVerify: true,
		}
	}

	options := &redis.Options{
		Addr:      addr,
		Password:  fg.BuildlogsRedis.Password,
		DB:        0,
		TLSConfig: tlsConfig,
	}
	if ok, err := shared.ValidateRedisConnection(options, "BUILDLOGS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Validate USER_EVENTS_REDIS connection
	if fg.UserEventsRedis.Engine == "rediscluster" {
		if opts.Mode != "testing" {
			clusterOpts := buildClusterOptions(fg.UserEventsRedis.Host, fg.UserEventsRedis.Port,
				fg.UserEventsRedis.Password, fg.UserEventsRedis.Ssl, fg.UserEventsRedis.RedisConfig)
			if ok, err := shared.ValidateRedisClusterConnection(clusterOpts, "USER_EVENTS_REDIS", "Redis"); !ok {
				errors = append(errors, err)
			}
		}
	} else {
		addr = fg.UserEventsRedis.Host
		if fg.UserEventsRedis.Port != 0 {
			addr = addr + ":" + fmt.Sprintf("%d", fg.UserEventsRedis.Port)
		}

		tlsConfig = nil
		if fg.UserEventsRedis.Ssl {
			tlsConfig = &tls.Config{
				InsecureSkipVerify: true,
			}
		}

		options = &redis.Options{
			Addr:      addr,
			Password:  fg.UserEventsRedis.Password,
			DB:        0,
			TLSConfig: tlsConfig,
		}
		if ok, err := shared.ValidateRedisConnection(options, "USER_EVENTS_REDIS", "Redis"); !ok {
			errors = append(errors, err)
		}
	}

	// Validate PULL_METRICS_REDIS connection (only if provided)
	if fg.PullMetricsRedis != nil {
		if fg.PullMetricsRedis.Engine == "rediscluster" {
			if opts.Mode != "testing" {
				clusterOpts := buildClusterOptions(fg.PullMetricsRedis.Host, fg.PullMetricsRedis.Port,
					fg.PullMetricsRedis.Password, fg.PullMetricsRedis.Ssl, fg.PullMetricsRedis.RedisConfig)
				if ok, err := shared.ValidateRedisClusterConnection(clusterOpts, "PULL_METRICS_REDIS", "Redis"); !ok {
					errors = append(errors, err)
				}
			}
		} else if opts.Mode != "testing" {
			addr = fg.PullMetricsRedis.Host
			if fg.PullMetricsRedis.Port != 0 {
				addr = addr + ":" + fmt.Sprintf("%d", fg.PullMetricsRedis.Port)
			}

			tlsConfig = nil
			if fg.PullMetricsRedis.Ssl {
				tlsConfig = &tls.Config{
					InsecureSkipVerify: true,
				}
			}

			options = &redis.Options{
				Addr:      addr,
				Password:  fg.PullMetricsRedis.Password,
				DB:        fg.PullMetricsRedis.Db,
				TLSConfig: tlsConfig,
			}
			if ok, err := shared.ValidateRedisConnection(options, "PULL_METRICS_REDIS", "Redis"); !ok {
				errors = append(errors, err)
			}
		}
	}

	return errors
}

// buildClusterOptions constructs redis.ClusterOptions from the struct fields and optional RedisConfig
func buildClusterOptions(host string, port int, password string, ssl bool, redisConfig *RedisConfigStruct) *redis.ClusterOptions {
	var addrs []string

	if redisConfig != nil && len(redisConfig.StartupNodes) > 0 {
		for _, node := range redisConfig.StartupNodes {
			nodeAddr := node.Host
			if node.Port != 0 {
				nodeAddr = nodeAddr + ":" + fmt.Sprintf("%d", node.Port)
			}
			addrs = append(addrs, nodeAddr)
		}
	}

	if len(addrs) == 0 && host != "" {
		addr := host
		if port != 0 {
			addr = addr + ":" + fmt.Sprintf("%d", port)
		}
		addrs = append(addrs, addr)
	}

	clusterPassword := password
	if redisConfig != nil && redisConfig.Password != "" {
		clusterPassword = redisConfig.Password
	}

	useSsl := ssl
	if redisConfig != nil && redisConfig.Ssl {
		useSsl = true
	}

	// Match DATA_MODEL_CACHE rediscluster validation: verify TLS certificates.
	var tlsConfig *tls.Config = nil
	if useSsl {
		tlsConfig = &tls.Config{
			InsecureSkipVerify: false,
		}
	}

	return &redis.ClusterOptions{
		Addrs:     addrs,
		Password:  clusterPassword,
		TLSConfig: tlsConfig,
	}
}
