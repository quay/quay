package signingengine

import (
	"errors"

	"github.com/creasty/defaults"
)

// SigningEngineFieldGroup represents the SigningEngineFieldGroup config fields
type SigningEngineFieldGroup struct {
	Gpg2PrivateKeyFilename string `default:"" validate:"" json:"GPG2_PRIVATE_KEY_FILENAME" yaml:"GPG2_PRIVATE_KEY_FILENAME"`
	Gpg2PrivateKeyName     string `default:"" validate:"" json:"GPG2_PRIVATE_KEY_NAME" yaml:"GPG2_PRIVATE_KEY_NAME"`
	Gpg2PublicKeyFilename  string `default:"" validate:"" json:"GPG2_PUBLIC_KEY_FILENAME" yaml:"GPG2_PUBLIC_KEY_FILENAME"`
	SigningEngine          string `default:"" validate:"" json:"SIGNING_ENGINE" yaml:"SIGNING_ENGINE"`
}

// NewSigningEngineFieldGroup creates a new SigningEngineFieldGroup
func NewSigningEngineFieldGroup(fullConfig map[string]interface{}) (*SigningEngineFieldGroup, error) {
	newSigningEngineFieldGroup := &SigningEngineFieldGroup{}
	defaults.Set(newSigningEngineFieldGroup)

	if value, ok := fullConfig["GPG2_PRIVATE_KEY_FILENAME"]; ok {
		newSigningEngineFieldGroup.Gpg2PrivateKeyFilename, ok = value.(string)
		if !ok {
			return newSigningEngineFieldGroup, errors.New("GPG2_PRIVATE_KEY_FILENAME must be of type string")
		}
	}
	if value, ok := fullConfig["GPG2_PRIVATE_KEY_NAME"]; ok {
		newSigningEngineFieldGroup.Gpg2PrivateKeyName, ok = value.(string)
		if !ok {
			return newSigningEngineFieldGroup, errors.New("GPG2_PRIVATE_KEY_NAME must be of type string")
		}
	}
	if value, ok := fullConfig["GPG2_PUBLIC_KEY_FILENAME"]; ok {
		newSigningEngineFieldGroup.Gpg2PublicKeyFilename, ok = value.(string)
		if !ok {
			return newSigningEngineFieldGroup, errors.New("GPG2_PUBLIC_KEY_FILENAME must be of type string")
		}
	}
	if value, ok := fullConfig["SIGNING_ENGINE"]; ok {
		newSigningEngineFieldGroup.SigningEngine, ok = value.(string)
		if !ok {
			return newSigningEngineFieldGroup, errors.New("SIGNING_ENGINE must be of type string")
		}
	}

	return newSigningEngineFieldGroup, nil
}
