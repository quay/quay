from typing import Dict

class FeatureNameValue(object):
    def __init__(self, name: str, value: bool): ...
    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...
    def __cmp__(self, other): ...
    def __bool__(self) -> bool: ...

def import_features(config_dict): ...
def get_features() -> Dict[str, FeatureNameValue]: ...

# Feature Flag: Whether sessions are permanent.
PERMANENT_SESSIONS: FeatureNameValue

# Feature Flag: Whether super users are supported.
SUPER_USERS: FeatureNameValue

# Feature Flag: Whether to allow anonymous users to browse and pull public repositories.
ANONYMOUS_ACCESS: FeatureNameValue

# Feature Flag: Whether billing is required.
BILLING: FeatureNameValue

# Feature Flag: Whether user accounts automatically have usage log access.
USER_LOG_ACCESS: FeatureNameValue

# Feature Flag: Whether GitHub login is supported.
GITHUB_LOGIN: FeatureNameValue

# Feature Flag: Whether Google login is supported.
GOOGLE_LOGIN: FeatureNameValue

# Feature Flag: Whether to support GitHub build triggers.
GITHUB_BUILD: FeatureNameValue

# Feature Flag: Whether to support Bitbucket build triggers.
BITBUCKET_BUILD: FeatureNameValue

# Feature Flag: Whether to support GitLab build triggers.
GITLAB_BUILD: FeatureNameValue

# Feature Flag: Dockerfile build support.
BUILD_SUPPORT: FeatureNameValue

# Feature Flag: Whether emails are enabled.
MAILING: FeatureNameValue

# Feature Flag: Whether users can be created (by non-super users).
USER_CREATION: FeatureNameValue

# Feature Flag: Whether users being created must be invited by another user.
# If USER_CREATION is off, this flag has no effect.
INVITE_ONLY_USER_CREATION: FeatureNameValue

# Feature Flag: Whether users can be renamed
USER_RENAME: FeatureNameValue

# Feature Flag: Whether non-encrypted passwords (as opposed to encrypted tokens) can be used for
# basic auth.
REQUIRE_ENCRYPTED_BASIC_AUTH: FeatureNameValue

# Feature Flag: Whether to automatically replicate between storage engines.
STORAGE_REPLICATION: FeatureNameValue

# Feature Flag: Whether users can directly login to the UI.
DIRECT_LOGIN: FeatureNameValue

# Feature Flag: Whether the v2/ endpoint is visible
ADVERTISE_V2: FeatureNameValue

# Feature Flag: Whether to restrict V1 pushes to the whitelist.
RESTRICTED_V1_PUSH: FeatureNameValue

# Feature Flag: Whether or not to rotate old action logs to storage.
ACTION_LOG_ROTATION: FeatureNameValue

# Feature Flag: Whether to enable conversion to ACIs.
ACI_CONVERSION: FeatureNameValue

# Feature Flag: Whether to allow for "namespace-less" repositories when pulling and pushing from
# Docker.
LIBRARY_SUPPORT: FeatureNameValue

# Feature Flag: Whether to require invitations when adding a user to a team.
REQUIRE_TEAM_INVITE: FeatureNameValue

# Feature Flag: Whether to proxy all direct download URLs in storage via the registry's nginx.
PROXY_STORAGE: FeatureNameValue

# Feature Flag: Whether to collect and support user metadata.
USER_METADATA: FeatureNameValue

# Feature Flag: Whether to support signing
SIGNING: FeatureNameValue

# Feature Flag: Whether to enable support for App repositories.
APP_REGISTRY: FeatureNameValue

# Feature Flag: Whether app registry is in a read-only mode.
READONLY_APP_REGISTRY: FeatureNameValue

# Feature Flag: If set to true, the _catalog endpoint returns public repositories. Otherwise,
# only private repositories can be returned.
PUBLIC_CATALOG: FeatureNameValue

# Feature Flag: If set to true, build logs may be read by those with read access to the repo,
# rather than only write access or admin access.
READER_BUILD_LOGS: FeatureNameValue

# Feature Flag: If set to true, autocompletion will apply to partial usernames.
PARTIAL_USER_AUTOCOMPLETE: FeatureNameValue

# Feature Flag: If set to true, users can confirm (and modify) their initial usernames when
# logging in via OIDC or a non-database internal auth provider.
USERNAME_CONFIRMATION: FeatureNameValue

# Feature Flag: If set to true, Quay will run using FIPS compliant hash functions.
FIPS: FeatureNameValue

# Security scanner
SECURITY_SCANNER: FeatureNameValue
SECURITY_NOTIFICATIONS: FeatureNameValue

# Repository mirror
REPO_MIRROR: FeatureNameValue

# Site key and secret key for using recaptcha.
RECAPTCHA: FeatureNameValue

# List of users allowed to pass through recaptcha security check to enable org/user creation via API
RECAPTCHA_WHITELISTED_USERS: FeatureNameValue

# Feature Flag: Whether team syncing from the backing auth is enabled.
TEAM_SYNCING: FeatureNameValue

# Feature Flag: If enabled, non-superusers can setup team syncing.
NONSUPERUSER_TEAM_SYNCING_SETUP: FeatureNameValue

# Feature Flag: Whether users can view and change their tag expiration.
CHANGE_TAG_EXPIRATION: FeatureNameValue

# Feature Flag: If enabled, users can create and use app specific tokens to login via the CLI.
APP_SPECIFIC_TOKENS: FeatureNameValue

# Feature Flag: Whether to record when users were last accessed.
USER_LAST_ACCESSED: FeatureNameValue

# Feature Flag: Whether to allow users to retrieve aggregated log counts.
AGGREGATED_LOG_COUNT_RETRIEVAL: FeatureNameValue

# Feature Flag: Whether rate limiting is enabled.
RATE_LIMITS: FeatureNameValue

# Feature Flag: Whether to support log exporting.
LOG_EXPORT: FeatureNameValue

# Feature Flag: Whether pull logs are disabled for free namespace.
DISABLE_PULL_LOGS_FOR_FREE_NAMESPACES: FeatureNameValue

# Feature Flag: If set to true, no account using blacklisted email addresses will be allowed
# to be created.
BLACKLISTED_EMAILS: FeatureNameValue

# Feature Flag: Whether garbage collection is enabled.
GARBAGE_COLLECTION: FeatureNameValue

# Feature Flags: Whether the workers for GCing deleted namespaces and repositories
# are enabled.
NAMESPACE_GARBAGE_COLLECTION: FeatureNameValue
REPOSITORY_GARBAGE_COLLECTION: FeatureNameValue

# Feature Flag: Whether to clear expired RepositoryActionCount entries.
CLEAR_EXPIRED_RAC_ENTRIES: FeatureNameValue

# Feature Flag: Whether OCI manifest support should be enabled generally.
GENERAL_OCI_SUPPORT: FeatureNameValue

# Feature Flag: Whether the repository action count worker is enabled.
REPOSITORY_ACTION_COUNTER: FeatureNameValue

# TEMP FEATURE: Backfill the sizes of manifests.
MANIFEST_SIZE_BACKFILL: FeatureNameValue

# Feature Flag: If set to true, the first User account may be created via API /api/v1/user/initialize
USER_INITIALIZE: FeatureNameValue

# Feature Flag: If set to true, notifications about vulnerabilities can be sent on new pushes
SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX: FeatureNameValue

# Allows "/" in repository names
EXTENDED_REPOSITORY_NAMES: FeatureNameValue

QUOTA_MANAGEMENT: FeatureNameValue

HELM_OCI_SUPPORT: FeatureNameValue

PROXY_CACHE: FeatureNameValue

RESTRICTED_USERS: FeatureNameValue
