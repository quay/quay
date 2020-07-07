package redis

import (
	"github.com/go-redis/redis/v8"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *RedisFieldGroup) Validate() []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// Check for build logs config
	if ok, err := shared.ValidateRequiredObject(fg.BuildlogsRedis, "BUILD_LOGS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
		return errors
	}

	// Check for build log host
	if ok, err := shared.ValidateRequiredString(fg.BuildlogsRedis.Host, "BUILD_LOGS_REDIS.HOST", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Check for user events config
	if ok, err := shared.ValidateRequiredObject(fg.UserEventsRedis, "USER_EVENTS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
		return errors
	}

	// Check for user events host
	if ok, err := shared.ValidateRequiredString(fg.BuildlogsRedis.Host, "USER_EVENTS_REDIS.HOST", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Build redis options for build logs
	options := &redis.Options{
		Addr:     fg.BuildlogsRedis.Host + ":" + string(fg.BuildlogsRedis.Port),
		Password: fg.BuildlogsRedis.Password,
		DB:       0,
	}
	if ok, err := shared.ValidateRedisConnection(options, "BUILD_LOGS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
	}

	// Build redis options for user events
	options = &redis.Options{
		Addr:     fg.UserEventsRedis.Host + ":" + string(fg.UserEventsRedis.Port),
		Password: fg.UserEventsRedis.Password,
		DB:       0,
	}
	if ok, err := shared.ValidateRedisConnection(options, "USER_EVENTS_REDIS", "Redis"); !ok {
		errors = append(errors, err)
	}

	return errors

}
