package lib

// TeamSyncingFieldGroup is a FieldGroup representing the Team Syncing settings
type TeamSyncingFieldGroup struct {

	// Whether to allow for team membership to be synced from a backing group in the
	// authentication engine (LDAP or Keystone)
	FeatureTeamSyncing bool `yaml:"FEATURE_TEAM_SYNCING,omitempty"`

	// If enabled, non-superusers can setup syncing on teams to backing LDAP or
	// Keystone. Defaults To False.
	FeatureNonSuperUserTeamSyncingSetup bool `yaml:"FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP,omitempty"`

	// If team syncing is enabled for a team, how often to check its membership and
	// resync if necessary (Default: 30m)
	TeamResyncStaleTime string `yaml:"TEAM_RESYNC_STALE_TIME,omitempty"`
}

// Validate assures that the field group contains valid settings
func (fg *TeamSyncingFieldGroup) Validate() (bool, error) {
	return true, nil
}
