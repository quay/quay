package redis

import (
	"crypto/tls"
	"fmt"

	"github.com/go-redis/redis/v8"
	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *RedisFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
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

	// Check for user events host
	if ok, err := shared.ValidateRequiredString(fg.UserEventsRedis.Host, "USER_EVENTS_REDIS.HOST", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Check for pull metrics config
	if ok, err := shared.ValidateRequiredObject(fg.PullMetricsRedis, "PULL_METRICS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
		return errors
	}

	// Check for pull metrics host
	if ok, err := shared.ValidateRequiredString(fg.PullMetricsRedis.Host, "PULL_METRICS_REDIS.HOST", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Build options for build logs and connect
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
	if opts.Mode != "testing" {
		if ok, err := shared.ValidateRedisConnection(options, "BUILDLOGS_REDIS", "Redis"); !ok {
			errors = append(errors, err)
		}
	}

	// Build options for user events and connect
	addr = fg.UserEventsRedis.Host
	if fg.UserEventsRedis.Port != 0 {
		addr = addr + ":" + fmt.Sprintf("%d", fg.BuildlogsRedis.Port)
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
	if opts.Mode != "testing" {
		if ok, err := shared.ValidateRedisConnection(options, "USER_EVENTS_REDIS", "Redis"); !ok {
			errors = append(errors, err)
		}
	}

	// Build options for pull metrics and connect
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
	if opts.Mode != "testing" {
		if ok, err := shared.ValidateRedisConnection(options, "PULL_METRICS_REDIS", "Redis"); !ok {
			errors = append(errors, err)
		}
	}

	return errors

}
