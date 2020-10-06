package repomirror

import (
	"errors"

	"github.com/creasty/defaults"
)

// RepoMirrorFieldGroup represents the RepoMirrorFieldGroup config fields
type RepoMirrorFieldGroup struct {
	FeatureRepoMirror        bool   `default:"false" validate:"" json:"FEATURE_REPO_MIRROR,omitempty" yaml:"FEATURE_REPO_MIRROR,omitempty"`
	RepoMirrorInterval       int    `default:"30" validate:"" json:"REPO_MIRROR_INTERVAL,omitempty" yaml:"REPO_MIRROR_INTERVAL,omitempty"`
	RepoMirrorServerHostname string `default:"" validate:"" json:"REPO_MIRROR_SERVER_HOSTNAME,omitempty" yaml:"REPO_MIRROR_SERVER_HOSTNAME,omitempty"`
	RepoMirrorTlsVerify      bool   `default:"true" validate:"" json:"REPO_MIRROR_TLS_VERIFY,omitempty" yaml:"REPO_MIRROR_TLS_VERIFY,omitempty"`
}

// NewRepoMirrorFieldGroup creates a new RepoMirrorFieldGroup
func NewRepoMirrorFieldGroup(fullConfig map[string]interface{}) (*RepoMirrorFieldGroup, error) {
	newRepoMirrorFieldGroup := &RepoMirrorFieldGroup{}
	defaults.Set(newRepoMirrorFieldGroup)

	if value, ok := fullConfig["FEATURE_REPO_MIRROR"]; ok {
		newRepoMirrorFieldGroup.FeatureRepoMirror, ok = value.(bool)
		if !ok {
			return newRepoMirrorFieldGroup, errors.New("FEATURE_REPO_MIRROR must be of type bool")
		}
	}
	if value, ok := fullConfig["REPO_MIRROR_INTERVAL"]; ok {
		newRepoMirrorFieldGroup.RepoMirrorInterval, ok = value.(int)
		if !ok {
			return newRepoMirrorFieldGroup, errors.New("REPO_MIRROR_INTERVAL must be of type int")
		}
	}
	if value, ok := fullConfig["REPO_MIRROR_SERVER_HOSTNAME"]; ok {
		newRepoMirrorFieldGroup.RepoMirrorServerHostname, ok = value.(string)
		if !ok {
			return newRepoMirrorFieldGroup, errors.New("REPO_MIRROR_SERVER_HOSTNAME must be of type string")
		}
	}
	if value, ok := fullConfig["REPO_MIRROR_TLS_VERIFY"]; ok {
		newRepoMirrorFieldGroup.RepoMirrorTlsVerify, ok = value.(bool)
		if !ok {
			return newRepoMirrorFieldGroup, errors.New("REPO_MIRROR_TLS_VERIFY must be of type bool")
		}
	}

	return newRepoMirrorFieldGroup, nil
}
