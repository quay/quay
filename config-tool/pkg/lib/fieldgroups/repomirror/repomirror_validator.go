package repomirror

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *RepoMirrorFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "RepoMirror"
	var errors []shared.ValidationError

	// Make sure feature is enabled
	if !fg.FeatureRepoMirror {
		return errors
	}

	// if repo mirror hostname is set, make sure its a valid hostname
	if fg.RepoMirrorServerHostname != "" {
		if ok, err := shared.ValidateIsHostname(fg.RepoMirrorServerHostname, "REPO_MIRROR_SERVER_HOSTNAME", fgName); !ok {
			errors = append(errors, err)
		}
	}

	return errors

}
