package generate

import (
	"errors"

	"github.com/quay/config-tool/pkg/lib/config"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/database"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/hostsettings"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/redis"
)

// AioiInputOptions defines the minimum required fields necessary for building a working config
type AioiInputOptions struct {
	DatabaseURI    string
	RedisHostname  string
	RedisPassword  string
	ServerHostname string
}

// GenerateBaseConfig will generate a minimal config for the Quay all in one installer.
// Database, Redis, and Server Hostname settings must be included
func GenerateBaseConfig(options AioiInputOptions) (config.Config, error) {

	// Check that all fields are correctly populated (this is a naive validtion)
	if options.DatabaseURI == "" {
		return nil, errors.New("Database URI is required")
	}
	if options.RedisHostname == "" {
		return nil, errors.New("Redis Hostname is required")
	}
	if options.RedisPassword == "" {
		return nil, errors.New("Redis Password is required")
	}
	if options.ServerHostname == "" {
		return nil, errors.New("Server Hostname is required")
	}

	defaultConfig, err := config.NewConfig(map[string]interface{}{})
	if err != nil {
		return defaultConfig, nil
	}

	// Set redis settings
	redisFieldGroup, err := redis.NewRedisFieldGroup(map[string]interface{}{})
	if err != nil {
		return defaultConfig, err
	}
	redisFieldGroup.BuildlogsRedis = &redis.BuildlogsRedisStruct{
		Host:     options.RedisHostname,
		Password: options.RedisPassword,
	}
	redisFieldGroup.UserEventsRedis = &redis.UserEventsRedisStruct{
		Host:     options.RedisHostname,
		Password: options.RedisPassword,
	}
	defaultConfig["Redis"] = redisFieldGroup

	// Set database settings
	databaseFieldGroup, err := database.NewDatabaseFieldGroup(map[string]interface{}{})
	if err != nil {
		return defaultConfig, err
	}
	databaseFieldGroup.DbUri = options.DatabaseURI
	defaultConfig["Database"] = databaseFieldGroup

	// Set host settings
	hostSettingsFieldGroup, err := hostsettings.NewHostSettingsFieldGroup(map[string]interface{}{})
	if err != nil {
		return defaultConfig, err
	}
	hostSettingsFieldGroup.ServerHostname = options.ServerHostname
	defaultConfig["HostSettings"] = hostSettingsFieldGroup

	return defaultConfig, nil
}
