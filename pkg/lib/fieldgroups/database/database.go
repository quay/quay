package database

import (
	"errors"

	"github.com/creasty/defaults"
)

// DatabaseFieldGroup represents the DatabaseFieldGroup config fields
type DatabaseFieldGroup struct {
	DbConnectionArgs *DbConnectionArgsStruct `default:"{}" validate:"" json:"DB_CONNECTION_ARGS,omitempty" yaml:"DB_CONNECTION_ARGS,omitempty"`
	DbUri            string                  `default:"" validate:"" json:"DB_URI,omitempty" yaml:"DB_URI,omitempty"`
}

// DbConnectionArgsStruct represents the DbConnectionArgsStruct config fields
type DbConnectionArgsStruct struct {
	Ssl          *SslStruct `default:"" validate:"" json:"ssl,omitempty" yaml:"ssl,omitempty"`
	Threadlocals bool       `default:"true" validate:"" json:"threadlocals" yaml:"threadlocals"`
	Autorollback bool       `default:"true" validate:"" json:"autorollback" yaml:"autorollback"`
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
