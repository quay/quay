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
	databaseURI    string
	redisHostname  string
	redisPassword  string
	serverHostname string
}

// GenerateBaseConfig will generate a minimal config for the Quay all in one installer.
// Database, Redis, and Server Hostname settings must be included
func GenerateBaseConfig(options AioiInputOptions) (config.Config, error) {

	// Check that all fields are correctly populated (this is a naive validtion)
	if options.databaseURI == "" {
		return nil, errors.New("Database URI is required")
	}
	if options.redisHostname == "" {
		return nil, errors.New("Redis Hostname is required")
	}
	if options.redisPassword == "" {
		return nil, errors.New("Redis Password is required")
	}
	if options.serverHostname == "" {
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
		Host:     options.redisHostname,
		Password: options.redisPassword,
	}
	redisFieldGroup.UserEventsRedis = &redis.UserEventsRedisStruct{
		Host:     options.redisHostname,
		Password: options.redisPassword,
	}
	defaultConfig["Redis"] = redisFieldGroup

	// Set database settings
	databaseFieldGroup, err := database.NewDatabaseFieldGroup(map[string]interface{}{})
	if err != nil {
		return defaultConfig, err
	}
	databaseFieldGroup.DbUri = options.databaseURI
	defaultConfig["Database"] = databaseFieldGroup

	// Set host settings
	hostSettingsFieldGroup, err := hostsettings.NewHostSettingsFieldGroup(map[string]interface{}{})
	if err != nil {
		return defaultConfig, err
	}
	hostSettingsFieldGroup.ServerHostname = options.serverHostname
	defaultConfig["HostSettings"] = hostSettingsFieldGroup

	return defaultConfig, nil
}
