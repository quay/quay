package elasticsearch

import (
	"errors"

	"github.com/creasty/defaults"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// ElasticSearchFieldGroup represents the ElasticSearchFieldGroup config fields
type ElasticSearchFieldGroup struct {
	LogsModel       string                 `default:"database" validate:"" yaml:"LOGS_MODEL"`
	LogsModelConfig *LogsModelConfigStruct `default:"" validate:"" yaml:"LOGS_MODEL_CONFIG"`
}

// LogsModelConfigStruct represents the LogsModelConfigStruct config fields
type LogsModelConfigStruct struct {
	KafkaConfig         *KafkaConfigStruct         `default:"" validate:"" yaml:"kafka_config"`
	ElasticsearchConfig *ElasticsearchConfigStruct `default:"" validate:"" yaml:"elasticsearch_config"`
	KinesisStreamConfig *KinesisStreamConfigStruct `default:"" validate:"" yaml:"kinesis_stream_config"`
	Producer            string                     `default:"" validate:"" yaml:"producer"`
}

// KinesisStreamConfigStruct represents the KinesisStreamConfigStruct config fields
type KinesisStreamConfigStruct struct {
	Retries            int    `default:"" validate:"" yaml:"retries"`
	ReadTimeout        int    `default:"" validate:"" yaml:"read_timeout"`
	MaxPoolConnections int    `default:"" validate:"" yaml:"max_pool_connections"`
	AwsRegion          string `default:"" validate:"" yaml:"aws_region"`
	ConnectTimeout     int    `default:"" validate:"" yaml:"connect_timeout"`
	AwsSecretKey       string `default:"" validate:"" yaml:"aws_secret_key"`
	StreamName         string `default:"" validate:"" yaml:"stream_name"`
	AwsAccessKey       string `default:"" validate:"" yaml:"aws_access_key"`
}

// ElasticsearchConfigStruct represents the ElasticsearchConfigStruct config fields
type ElasticsearchConfigStruct struct {
	AwsRegion     string               `default:"" validate:"" yaml:"aws_region"`
	Port          int                  `default:"" validate:"" yaml:"port"`
	AccessKey     string               `default:"" validate:"" yaml:"access_key"`
	Host          string               `default:"" validate:"" yaml:"host"`
	IndexPrefix   string               `default:"logentry_" validate:"" yaml:"index_prefix"`
	IndexSettings *IndexSettingsStruct `default:"" validate:"" yaml:"index_settings"`
	UseSsl        bool                 `default:"true" validate:"" yaml:"use_ssl"`
	SecretKey     string               `default:"" validate:"" yaml:"secret_key"`
}

// IndexSettingsStruct represents the IndexSettings struct
type IndexSettingsStruct map[string]interface{}

// KafkaConfigStruct represents the KafkaConfigStruct config fields
type KafkaConfigStruct struct {
	Topic            string        `default:"" validate:"" yaml:"topic"`
	BootstrapServers []interface{} `default:"" validate:"" yaml:"bootstrap_servers"`
	MaxBlockSeconds  int           `default:"" validate:"" yaml:"max_block_seconds"`
}

// NewElasticSearchFieldGroup creates a new ElasticSearchFieldGroup
func NewElasticSearchFieldGroup(fullConfig map[string]interface{}) (*ElasticSearchFieldGroup, error) {
	newElasticSearchFieldGroup := &ElasticSearchFieldGroup{}
	defaults.Set(newElasticSearchFieldGroup)

	if value, ok := fullConfig["LOGS_MODEL"]; ok {
		newElasticSearchFieldGroup.LogsModel, ok = value.(string)
		if !ok {
			return newElasticSearchFieldGroup, errors.New("LOGS_MODEL must be of type string")
		}
	}
	if value, ok := fullConfig["LOGS_MODEL_CONFIG"]; ok {
		var err error
		value := shared.FixInterface(value.(map[interface{}]interface{}))
		newElasticSearchFieldGroup.LogsModelConfig, err = NewLogsModelConfigStruct(value)
		if err != nil {
			return newElasticSearchFieldGroup, err
		}
	}

	return newElasticSearchFieldGroup, nil
}

// NewLogsModelConfigStruct creates a new LogsModelConfigStruct
func NewLogsModelConfigStruct(fullConfig map[string]interface{}) (*LogsModelConfigStruct, error) {
	newLogsModelConfigStruct := &LogsModelConfigStruct{}
	defaults.Set(newLogsModelConfigStruct)

	if value, ok := fullConfig["kafka_config"]; ok {
		var err error
		value := shared.FixInterface(value.(map[interface{}]interface{}))
		newLogsModelConfigStruct.KafkaConfig, err = NewKafkaConfigStruct(value)
		if err != nil {
			return newLogsModelConfigStruct, err
		}
	}
	if value, ok := fullConfig["elasticsearch_config"]; ok {
		var err error
		value := shared.FixInterface(value.(map[interface{}]interface{}))
		newLogsModelConfigStruct.ElasticsearchConfig, err = NewElasticsearchConfigStruct(value)
		if err != nil {
			return newLogsModelConfigStruct, err
		}
	}
	if value, ok := fullConfig["kinesis_stream_config"]; ok {
		var err error
		value := shared.FixInterface(value.(map[interface{}]interface{}))
		newLogsModelConfigStruct.KinesisStreamConfig, err = NewKinesisStreamConfigStruct(value)
		if err != nil {
			return newLogsModelConfigStruct, err
		}
	}
	if value, ok := fullConfig["producer"]; ok {
		newLogsModelConfigStruct.Producer, ok = value.(string)
		if !ok {
			return newLogsModelConfigStruct, errors.New("producer must be of type string")
		}
	}

	return newLogsModelConfigStruct, nil
}

// NewKinesisStreamConfigStruct creates a new KinesisStreamConfigStruct
func NewKinesisStreamConfigStruct(fullConfig map[string]interface{}) (*KinesisStreamConfigStruct, error) {
	newKinesisStreamConfigStruct := &KinesisStreamConfigStruct{}
	defaults.Set(newKinesisStreamConfigStruct)

	if value, ok := fullConfig["retries"]; ok {
		newKinesisStreamConfigStruct.Retries, ok = value.(int)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("retries must be of type int")
		}
	}
	if value, ok := fullConfig["read_timeout"]; ok {
		newKinesisStreamConfigStruct.ReadTimeout, ok = value.(int)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("read_timeout must be of type int")
		}
	}
	if value, ok := fullConfig["max_pool_connections"]; ok {
		newKinesisStreamConfigStruct.MaxPoolConnections, ok = value.(int)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("max_pool_connections must be of type int")
		}
	}
	if value, ok := fullConfig["aws_region"]; ok {
		newKinesisStreamConfigStruct.AwsRegion, ok = value.(string)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("aws_region must be of type string")
		}
	}
	if value, ok := fullConfig["connect_timeout"]; ok {
		newKinesisStreamConfigStruct.ConnectTimeout, ok = value.(int)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("connect_timeout must be of type int")
		}
	}
	if value, ok := fullConfig["aws_secret_key"]; ok {
		newKinesisStreamConfigStruct.AwsSecretKey, ok = value.(string)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("aws_secret_key must be of type string")
		}
	}
	if value, ok := fullConfig["stream_name"]; ok {
		newKinesisStreamConfigStruct.StreamName, ok = value.(string)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("stream_name must be of type string")
		}
	}
	if value, ok := fullConfig["aws_access_key"]; ok {
		newKinesisStreamConfigStruct.AwsAccessKey, ok = value.(string)
		if !ok {
			return newKinesisStreamConfigStruct, errors.New("aws_access_key must be of type string")
		}
	}

	return newKinesisStreamConfigStruct, nil
}

// NewElasticsearchConfigStruct creates a new ElasticsearchConfigStruct
func NewElasticsearchConfigStruct(fullConfig map[string]interface{}) (*ElasticsearchConfigStruct, error) {
	newElasticsearchConfigStruct := &ElasticsearchConfigStruct{}
	defaults.Set(newElasticsearchConfigStruct)

	if value, ok := fullConfig["aws_region"]; ok {
		newElasticsearchConfigStruct.AwsRegion, ok = value.(string)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("aws_region must be of type string")
		}
	}
	if value, ok := fullConfig["port"]; ok {
		newElasticsearchConfigStruct.Port, ok = value.(int)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("port must be of type int")
		}
	}
	if value, ok := fullConfig["access_key"]; ok {
		newElasticsearchConfigStruct.AccessKey, ok = value.(string)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("access_key must be of type string")
		}
	}
	if value, ok := fullConfig["host"]; ok {
		newElasticsearchConfigStruct.Host, ok = value.(string)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("host must be of type string")
		}
	}
	if value, ok := fullConfig["index_prefix"]; ok {
		newElasticsearchConfigStruct.IndexPrefix, ok = value.(string)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("index_prefix must be of type string")
		}
	}
	if value, ok := fullConfig["index_settings"]; ok {
		var err error
		value := shared.FixInterface(value.(map[interface{}]interface{}))
		newElasticsearchConfigStruct.IndexSettings, err = NewIndexSettingsStruct(value)
		if err != nil {
			return newElasticsearchConfigStruct, err
		}
	}
	if value, ok := fullConfig["use_ssl"]; ok {
		newElasticsearchConfigStruct.UseSsl, ok = value.(bool)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("use_ssl must be of type bool")
		}
	}
	if value, ok := fullConfig["secret_key"]; ok {
		newElasticsearchConfigStruct.SecretKey, ok = value.(string)
		if !ok {
			return newElasticsearchConfigStruct, errors.New("secret_key must be of type string")
		}
	}

	return newElasticsearchConfigStruct, nil
}

// NewIndexSettingsStruct creates a new IndexSettingsStruct
func NewIndexSettingsStruct(fullConfig map[string]interface{}) (*IndexSettingsStruct, error) {
	newIndexSettingsStruct := IndexSettingsStruct{}
	for key, value := range fullConfig {
		newIndexSettingsStruct[key] = value
	}
	return &newIndexSettingsStruct, nil
}

// NewKafkaConfigStruct creates a new KafkaConfigStruct
func NewKafkaConfigStruct(fullConfig map[string]interface{}) (*KafkaConfigStruct, error) {
	newKafkaConfigStruct := &KafkaConfigStruct{}
	defaults.Set(newKafkaConfigStruct)

	if value, ok := fullConfig["topic"]; ok {
		newKafkaConfigStruct.Topic, ok = value.(string)
		if !ok {
			return newKafkaConfigStruct, errors.New("topic must be of type string")
		}
	}
	if value, ok := fullConfig["bootstrap_servers"]; ok {
		newKafkaConfigStruct.BootstrapServers, ok = value.([]interface{})
		if !ok {
			return newKafkaConfigStruct, errors.New("bootstrap_servers must be of type []interface{}")
		}
	}
	if value, ok := fullConfig["max_block_seconds"]; ok {
		newKafkaConfigStruct.MaxBlockSeconds, ok = value.(int)
		if !ok {
			return newKafkaConfigStruct, errors.New("max_block_seconds must be of type int")
		}
	}

	return newKafkaConfigStruct, nil
}
