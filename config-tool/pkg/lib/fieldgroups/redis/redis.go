package redis

import (
	"errors"

	"github.com/creasty/defaults"
)

// RedisFieldGroup represents the RedisFieldGroup config fields
type RedisFieldGroup struct {
	BuildlogsRedis   *BuildlogsRedisStruct   `default:"" validate:"" json:"BUILDLOGS_REDIS,omitempty" yaml:"BUILDLOGS_REDIS,omitempty"`
	UserEventsRedis  *UserEventsRedisStruct  `default:"" validate:"" json:"USER_EVENTS_REDIS,omitempty" yaml:"USER_EVENTS_REDIS,omitempty"`
	PullMetricsRedis *PullMetricsRedisStruct `default:"" validate:"" json:"PULL_METRICS_REDIS,omitempty" yaml:"PULL_METRICS_REDIS,omitempty"`
}

// UserEventsRedisStruct represents the UserEventsRedisStruct config fields
type UserEventsRedisStruct struct {
	Password string `default:"" validate:"" json:"password,omitempty" yaml:"password,omitempty"`
	Port     int    `default:"" validate:"" json:"port,omitempty" yaml:"port,omitempty"`
	Host     string `default:"" validate:"" json:"host,omitempty" yaml:"host,omitempty"`
	Ssl      bool   `default:"false" validate:"" json:"ssl,omitempty" yaml:"ssl,omitempty"`
}

// BuildlogsRedisStruct represents the BuildlogsRedisStruct config fields
type BuildlogsRedisStruct struct {
	Password string `default:"" validate:"" json:"password,omitempty" yaml:"password,omitempty"`
	Port     int    `default:"" validate:"" json:"port,omitempty" yaml:"port,omitempty"`
	Host     string `default:"" validate:"" json:"host,omitempty" yaml:"host,omitempty"`
	Ssl      bool   `default:"false" validate:"" json:"ssl,omitempty" yaml:"ssl,omitempty"`
}

// PullMetricsRedisStruct represents the PullMetricsRedisStruct config fields
type PullMetricsRedisStruct struct {
	Password string `default:"" validate:"" json:"password,omitempty" yaml:"password,omitempty"`
	Port     int    `default:"" validate:"" json:"port,omitempty" yaml:"port,omitempty"`
	Host     string `default:"" validate:"" json:"host,omitempty" yaml:"host,omitempty"`
	Ssl      bool   `default:"false" validate:"" json:"ssl,omitempty" yaml:"ssl,omitempty"`
	Db       int    `default:"1" validate:"" json:"db,omitempty" yaml:"db,omitempty"`
}

// NewRedisFieldGroup creates a new RedisFieldGroup
func NewRedisFieldGroup(fullConfig map[string]interface{}) (*RedisFieldGroup, error) {
	newRedisFieldGroup := &RedisFieldGroup{}
	defaults.Set(newRedisFieldGroup)

	if value, ok := fullConfig["BUILDLOGS_REDIS"]; ok {
		var err error
		value := value.(map[string]interface{})
		newRedisFieldGroup.BuildlogsRedis, err = NewBuildlogsRedisStruct(value)
		if err != nil {
			return newRedisFieldGroup, err
		}
	}
	if value, ok := fullConfig["USER_EVENTS_REDIS"]; ok {
		var err error
		value := value.(map[string]interface{})
		newRedisFieldGroup.UserEventsRedis, err = NewUserEventsRedisStruct(value)
		if err != nil {
			return newRedisFieldGroup, err
		}
	}
	if value, ok := fullConfig["PULL_METRICS_REDIS"]; ok {
		var err error
		value := value.(map[string]interface{})
		newRedisFieldGroup.PullMetricsRedis, err = NewPullMetricsRedisStruct(value)
		if err != nil {
			return newRedisFieldGroup, err
		}
	}

	return newRedisFieldGroup, nil
}

// NewUserEventsRedisStruct creates a new UserEventsRedisStruct
func NewUserEventsRedisStruct(fullConfig map[string]interface{}) (*UserEventsRedisStruct, error) {
	newUserEventsRedisStruct := &UserEventsRedisStruct{}
	defaults.Set(newUserEventsRedisStruct)

	if value, ok := fullConfig["password"]; ok {
		newUserEventsRedisStruct.Password, ok = value.(string)
		if !ok {
			return newUserEventsRedisStruct, errors.New("password must be of type string")
		}
	}
	if value, ok := fullConfig["port"]; ok {
		newUserEventsRedisStruct.Port, ok = value.(int)
		if !ok {
			return newUserEventsRedisStruct, errors.New("port must be of type int")
		}
	}
	if value, ok := fullConfig["host"]; ok {
		newUserEventsRedisStruct.Host, ok = value.(string)
		if !ok {
			return newUserEventsRedisStruct, errors.New("host must be of type string")
		}
	}

	if value, ok := fullConfig["ssl"]; ok {
		newUserEventsRedisStruct.Ssl, ok = value.(bool)
		if !ok {
			return newUserEventsRedisStruct, errors.New("ssl must be of type bool")
		}
	}

	return newUserEventsRedisStruct, nil
}

// NewBuildlogsRedisStruct creates a new BuildlogsRedisStruct
func NewBuildlogsRedisStruct(fullConfig map[string]interface{}) (*BuildlogsRedisStruct, error) {
	newBuildlogsRedisStruct := &BuildlogsRedisStruct{}
	defaults.Set(newBuildlogsRedisStruct)

	if value, ok := fullConfig["password"]; ok {
		newBuildlogsRedisStruct.Password, ok = value.(string)
		if !ok {
			return newBuildlogsRedisStruct, errors.New("password must be of type string")
		}
	}
	if value, ok := fullConfig["port"]; ok {
		newBuildlogsRedisStruct.Port, ok = value.(int)
		if !ok {
			return newBuildlogsRedisStruct, errors.New("port must be of type int")
		}
	}
	if value, ok := fullConfig["host"]; ok {
		newBuildlogsRedisStruct.Host, ok = value.(string)
		if !ok {
			return newBuildlogsRedisStruct, errors.New("host must be of type string")
		}
	}

	if value, ok := fullConfig["ssl"]; ok {
		newBuildlogsRedisStruct.Ssl, ok = value.(bool)
		if !ok {
			return newBuildlogsRedisStruct, errors.New("ssl must be of type bool")
		}
	}

	return newBuildlogsRedisStruct, nil
}

// NewPullMetricsRedisStruct creates a new PullMetricsRedisStruct
func NewPullMetricsRedisStruct(fullConfig map[string]interface{}) (*PullMetricsRedisStruct, error) {
	newPullMetricsRedisStruct := &PullMetricsRedisStruct{}
	defaults.Set(newPullMetricsRedisStruct)

	if value, ok := fullConfig["password"]; ok {
		newPullMetricsRedisStruct.Password, ok = value.(string)
		if !ok {
			return newPullMetricsRedisStruct, errors.New("password must be of type string")
		}
	}
	if value, ok := fullConfig["port"]; ok {
		newPullMetricsRedisStruct.Port, ok = value.(int)
		if !ok {
			return newPullMetricsRedisStruct, errors.New("port must be of type int")
		}
	}
	if value, ok := fullConfig["host"]; ok {
		newPullMetricsRedisStruct.Host, ok = value.(string)
		if !ok {
			return newPullMetricsRedisStruct, errors.New("host must be of type string")
		}
	}
	if value, ok := fullConfig["ssl"]; ok {
		newPullMetricsRedisStruct.Ssl, ok = value.(bool)
		if !ok {
			return newPullMetricsRedisStruct, errors.New("ssl must be of type bool")
		}
	}
	if value, ok := fullConfig["db"]; ok {
		newPullMetricsRedisStruct.Db, ok = value.(int)
		if !ok {
			return newPullMetricsRedisStruct, errors.New("db must be of type int")
		}
	}

	return newPullMetricsRedisStruct, nil
}
