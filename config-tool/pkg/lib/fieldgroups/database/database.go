package database

import (
	"errors"

	"github.com/creasty/defaults"
)

// DatabaseFieldGroup represents the DatabaseFieldGroup config fields
type DatabaseFieldGroup struct {
	DbConnectionArgs *DbConnectionArgsStruct `default:"{}" json:"DB_CONNECTION_ARGS,omitempty" yaml:"DB_CONNECTION_ARGS,omitempty"`
	DbUri            string                  `default:"" validate:"" json:"DB_URI,omitempty" yaml:"DB_URI,omitempty"`
}

// DbConnectionArgsStruct represents the DbConnectionArgsStruct config fields
type DbConnectionArgsStruct struct {
	// MySQL arguments
	Ssl          *SslStruct `default:""  json:"ssl,omitempty" yaml:"ssl,omitempty"`
	Threadlocals bool       `default:""  json:"threadlocals,omitempty" yaml:"threadlocals,omitempty"`
	Autorollback bool       `default:""  json:"autorollback,omitempty" yaml:"autorollback,omitempty"`

	// Postgres arguments
	SslRootCert           string `default:""  json:"sslrootcert,omitempty" yaml:"sslrootcert,omitempty"`
	SslMode               string `default:""  json:"sslmode,omitempty" yaml:"sslmode,omitempty"`
	SslCert               string `default:""  json:"sslcert,omitempty" yaml:"sslcert,omitempty"`
	SslKey                string `default:""  json:"sslkey,omitempty" yaml:"sslkey,omitempty"`
	SslSni                string `default:""  json:"sslsni,omitempty" yaml:"sslsni,omitempty"`
	SslMinProtocolVersion string `default:""  json:"ssl_min_protocol_version,omitempty" yaml:"ssl_min_protocol_version,omitempty"`
	SslMaxProtocolVersion string `default:""  json:"ssl_max_protocol_version,omitempty" yaml:"ssl_max_protocol_version,omitempty"`
	SslCrl                string `default:""  json:"sslcrl,omitempty" yaml:"sslcrl,omitempty"`
	SslCrlDir             string `default:""  json:"sslcrldir,omitempty" yaml:"sslcrldir,omitempty"`
	SslCompression        *int   `default:""  json:"sslcompression,omitempty" yaml:"sslcompression,omitempty"`

	// Network arguments
	Keepalives          *int `default:""  json:"keepalives,omitempty" yaml:"keepalives,omitempty"`
	Keepalives_Idle     *int `default:""  json:"keepalives_idle,omitempty" yaml:"keepalives_idle,omitempty"`
	Keepalives_Interval *int `default:""  json:"keepalives_interval,omitempty" yaml:"keepalives_interval,omitempty"`
	Keepalives_Count    *int `default:""  json:"keepalives_count,omitempty" yaml:"keepalives_count,omitempty"`
	Tcp_User_Timeout    *int `default:""  json:"tcp_user_timeout,omitempty" yaml:"tcp_user_timeout,omitempty"`
}

// SslStruct represents the SslStruct config fields
type SslStruct struct {
	Ca string `default:"" validate:"" json:"ca,omitempty" yaml:"ca,omitempty"`
}

// NewDatabaseFieldGroup creates a new DatabaseFieldGroup
func NewDatabaseFieldGroup(fullConfig map[string]interface{}) (*DatabaseFieldGroup, error) {
	newDatabaseFieldGroup := &DatabaseFieldGroup{}
	defaults.Set(newDatabaseFieldGroup)

	if value, ok := fullConfig["DB_CONNECTION_ARGS"]; ok {
		var err error
		value := value.(map[string]interface{})
		newDatabaseFieldGroup.DbConnectionArgs, err = NewDbConnectionArgsStruct(value)
		if err != nil {
			return newDatabaseFieldGroup, err
		}
	}
	if value, ok := fullConfig["DB_URI"]; ok {
		newDatabaseFieldGroup.DbUri, ok = value.(string)
		if !ok {
			return newDatabaseFieldGroup, errors.New("DB_URI must be of type string")
		}
	}

	return newDatabaseFieldGroup, nil
}

// function to ensure supported TLS versions are used in Postgres connection URI
func IsValidTLS(version string) bool {
	switch version {
	case
		"TLSv1",
		"TLSv1.1",
		"TLSv1.2",
		"TLSv1.3":
		return true
	}
	return false
}

// NewDbConnectionArgsStruct creates a new DbConnectionArgsStruct
func NewDbConnectionArgsStruct(fullConfig map[string]interface{}) (*DbConnectionArgsStruct, error) {
	newDbConnectionArgsStruct := &DbConnectionArgsStruct{}
	defaults.Set(newDbConnectionArgsStruct)

	if value, ok := fullConfig["ssl"]; ok {
		var err error
		value := value.(map[string]interface{})
		newDbConnectionArgsStruct.Ssl, err = NewSslStruct(value)
		if err != nil {
			return newDbConnectionArgsStruct, err
		}
	}
	if value, ok := fullConfig["threadlocals"]; ok {
		newDbConnectionArgsStruct.Threadlocals, ok = value.(bool)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("threadlocals must be of type bool")
		}
	}
	if value, ok := fullConfig["autorollback"]; ok {
		newDbConnectionArgsStruct.Autorollback, ok = value.(bool)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("autorollback must be of type bool")
		}
	}
	if value, ok := fullConfig["sslmode"]; ok {
		newDbConnectionArgsStruct.SslMode, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslmode must be of type string")
		}
	}
	if value, ok := fullConfig["sslrootcert"]; ok {
		newDbConnectionArgsStruct.SslRootCert, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslrootcert must be of type string")
		}
	}
	if value, ok := fullConfig["sslcert"]; ok {
		newDbConnectionArgsStruct.SslCert, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslcert must be of type string")
		}
	}
	if value, ok := fullConfig["sslkey"]; ok {
		newDbConnectionArgsStruct.SslKey, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslkey must be of type string")
		}
	}
	if value, ok := fullConfig["sslsni"]; ok {
		newDbConnectionArgsStruct.SslSni, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslsni must be of type string")
		}
	}
	if value, ok := fullConfig["ssl_min_protocolversion"]; ok {
		newDbConnectionArgsStruct.SslMinProtocolVersion, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("ssl_min_protoclversion must be of type string")
		}
		if !IsValidTLS(value.(string)) {
			return newDbConnectionArgsStruct, errors.New("ssl_min_protoclversion invalid value (supported TLSv1,TLSv1.1-TLSv1.3)")
		}
	}
	if value, ok := fullConfig["ssl_max_protocolversion"]; ok {
		newDbConnectionArgsStruct.SslMaxProtocolVersion, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("ssl_max_protoclversion must be of type string")
		}
		if !IsValidTLS(value.(string)) {
			return newDbConnectionArgsStruct, errors.New("ssl_max_protoclversion invalid value (supported TLSv1,TLSv1.1-TLSv1.3)")
		}
	}
	if value, ok := fullConfig["sslcrl"]; ok {
		newDbConnectionArgsStruct.SslCrl, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslcrl must be of type string")
		}
	}
	if value, ok := fullConfig["sslcrldir"]; ok {
		newDbConnectionArgsStruct.SslCrlDir, ok = value.(string)
		if !ok {
			return newDbConnectionArgsStruct, errors.New("sslcrldir must be of type string")
		}
	}

	if value, ok := fullConfig["sslcompression"]; ok {
		val, ok := value.(int)
		if !ok {
			_, ok = value.(int)
			if !ok {
				return newDbConnectionArgsStruct, errors.New("sslcompression must be of type int")
			}
		}
		newDbConnectionArgsStruct.SslCompression = &val
	}
	if value, ok := fullConfig["keepalives"]; ok {
		val, ok := value.(int)
		if !ok {
			_, ok = value.(int)
			if !ok {
				return newDbConnectionArgsStruct, errors.New("keepalives must be of type int")
			}
		}
		newDbConnectionArgsStruct.Keepalives = &val
	}
	if value, ok := fullConfig["keepalives_idle"]; ok {
		val, ok := value.(int)
		if !ok {
			_, ok = value.(int)
			if !ok {
				return newDbConnectionArgsStruct, errors.New("keepalives_idle must be of type int")
			}
		}
		newDbConnectionArgsStruct.Keepalives_Idle = &val
	}
	if value, ok := fullConfig["keepalives_interval"]; ok {
		val, ok := value.(int)
		if !ok {
			_, ok = value.(int)
			if !ok {
				return newDbConnectionArgsStruct, errors.New("keepalives_interval must be of type int")
			}
		}
		newDbConnectionArgsStruct.Keepalives_Interval = &val
	}
	if value, ok := fullConfig["keepalives_count"]; ok {
		val, ok := value.(int)
		if !ok {
			_, ok = value.(int)
			if !ok {
				return newDbConnectionArgsStruct, errors.New("keepalives_count must be of type int")
			}
		}
		newDbConnectionArgsStruct.Keepalives_Count = &val
	}
	if value, ok := fullConfig["tcp_user_timeout"]; ok {
		val, ok := value.(int)
		if !ok {
			_, ok = value.(int)
			if !ok {
				return newDbConnectionArgsStruct, errors.New("tcp_user_timeout must be of type int")
			}
		}
		newDbConnectionArgsStruct.Tcp_User_Timeout = &val
	}

	return newDbConnectionArgsStruct, nil
}

// NewSslStruct creates a new SslStruct
func NewSslStruct(fullConfig map[string]interface{}) (*SslStruct, error) {
	newSslStruct := &SslStruct{}
	defaults.Set(newSslStruct)

	if value, ok := fullConfig["ca"]; ok {
		newSslStruct.Ca, ok = value.(string)
		if !ok {
			return newSslStruct, errors.New("ca must be of type string")
		}
	}

	return newSslStruct, nil
}
