package teamsyncing

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *TeamSyncingFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// If resync stale time has bad pattern
	if ok, err := shared.ValidateTimePattern(fg.TeamResyncStaleTime, "TEAM_RESYNC_STALE_TIME", "TeamSyncing"); !ok {
		errors = append(errors, err)
	}

	// Return errors
	return errors

}
