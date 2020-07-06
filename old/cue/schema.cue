import "list"

// Schema for Quay configuration
@jsonschema(schema="http://json-schema.org/draft-07/schema")

// Whether users can directly login to the UI. Defaults to True
FEATURE_DIRECT_LOGIN?: bool

// Whether GitHub login is supported. Defaults to False
FEATURE_GITHUB_LOGIN?: bool

// Whether Google login is supported. Defaults to False
FEATURE_GOOGLE_LOGIN?: bool

// Whether users can be created (by non-super users). Defaults to
// True
FEATURE_USER_CREATION?: bool

// Whether users being created must be invited by another user.
// Defaults to False
FEATURE_INVITE_ONLY_USER_CREATION?: bool

// Whether or not to rotate old action logs to storage. Defaults
// to False
FEATURE_ACTION_LOG_ROTATION?: bool

// If action log archiving is enabled, the path in storage in
// which to place the archived data.
ACTION_LOG_ARCHIVE_PATH?: string

// If action log archiving is enabled, the storage engine in which
// to place the archived data.
ACTION_LOG_ARCHIVE_LOCATION?: string

// Configuration for storage engine(s) to use in Quay. Each key is
// a unique ID for a storage engine, with the value being a tuple
// of the type and configuration for that engine.
DISTRIBUTED_STORAGE_CONFIG?: {
	{[=~"^.*$" & !~"^()$"]: [...]}
	...
}

// If specified, the long-form title for the registry. Defaults to
// `Red Hat Quay`.
REGISTRY_TITLE?: string

// If specified, the short-form title for the registry. Defaults
// to `Red Hat Quay`.
REGISTRY_TITLE_SHORT?: string

// Number of results returned per page by search page. Defaults to
// 10
SEARCH_RESULTS_PER_PAGE?: number

// Maximum number of pages the user can paginate in search before
// they are limited. Defaults to 10
SEARCH_MAX_RESULT_PAGE_COUNT?: number

// If specified, contact information to display on the contact
// page. If only a single piece of contact information is
// specified, the contact footer will link directly.
CONTACT_INFO?: list.UniqueItems() & [=~"^mailto:(.)+$", =~"^irc://(.)+$", =~"^tel:(.)+$", =~"^http(s)?://(.)+$"]

// The types of avatars to display, either generated inline
// (local) or Gravatar (gravatar)
AVATAR_KIND?: "local" | "gravatar"

// Custom branding for logos and URLs in the Quay UI
BRANDING?: {
	// Main logo image URL
	logo: string

	// Logo for UI footer
	footer_img?: string

	// Link for footer image
	footer_url?: string
	...
}

// Root URL for documentation links
DOCUMENTATION_ROOT?: string

// Whether to allow for team membership to be synced from a
// backing group in the authentication engine (LDAP or Keystone)
FEATURE_TEAM_SYNCING?: bool

// If enabled, non-superusers can setup syncing on teams to
// backing LDAP or Keystone. Defaults To False.
FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP?: bool

// If team syncing is enabled for a team, how often to check its
// membership and resync if necessary (Default: 30m)
TEAM_RESYNC_STALE_TIME?: =~"^[0-9]+(w|m|d|h|s)$"

// The authentication engine to use for credential authentication.
AUTHENTICATION_TYPE?: "Database" | "LDAP" | "JWT" | "Keystone" | "OIDC" | "AppToken"

// If enabled, users can create tokens for use by the Docker CLI.
// Defaults to True
FEATURE_APP_SPECIFIC_TOKENS?: bool

// Whether to turn of/off the security scanner. Defaults to False
FEATURE_SECURITY_SCANNER?: bool

// The endpoint for the V2 security scanner
SECURITY_SCANNER_ENDPOINT?: =~"^http(s)?://(.)+$"

// Whether or not to the security scanner notification feature
SECURITY_SCANNER_NOTIFICATIONS?: bool

// The number of seconds between indexing intervals in the
// security scanner. Defaults to 30.
SECURITY_SCANNER_INDEXING_INTERVAL?: number
...
