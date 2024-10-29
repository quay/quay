import os.path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import requests

from _init import CONF_DIR, ROOT_DIR


def build_requests_session():
    sess = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess


# The set of configuration key names that will be accessible in the client. Since these
# values are sent to the frontend, DO NOT PLACE ANY SECRETS OR KEYS in this list.
CLIENT_WHITELIST = [
    "SERVER_HOSTNAME",
    "PREFERRED_URL_SCHEME",
    "MIXPANEL_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "ENTERPRISE_LOGO_URL",
    "SENTRY_PUBLIC_DSN",
    "AUTHENTICATION_TYPE",
    "REGISTRY_TITLE",
    "REGISTRY_TITLE_SHORT",
    "CONTACT_INFO",
    "AVATAR_KIND",
    "LOCAL_OAUTH_HANDLER",
    "SETUP_COMPLETE",
    "DEBUG",
    "MARKETO_MUNCHKIN_ID",
    "STATIC_SITE_BUCKET",
    "RECAPTCHA_SITE_KEY",
    "CHANNEL_COLORS",
    "TAG_EXPIRATION_OPTIONS",
    "INTERNAL_OIDC_SERVICE_ID",
    "SEARCH_RESULTS_PER_PAGE",
    "SEARCH_MAX_RESULT_PAGE_COUNT",
    "BRANDING",
    "DOCUMENTATION_ROOT",
    "FEATURE_REPO_MIRROR",
    "FEATURE_QUOTA_MANAGEMENT",
    "FEATURE_EDIT_QUOTA",
    "FEATURE_PROXY_CACHE",
    "QUOTA_BACKFILL",
    "PERMANENTLY_DELETE_TAGS",
    "UI_V2_FEEDBACK_FORM",
    "TERMS_OF_SERVICE_URL",
    "UI_DELAY_AFTER_WRITE_SECONDS",
    "FEATURE_ASSIGN_OAUTH_TOKEN",
    "FEATURE_IMAGE_EXPIRY_TRIGGER",
    "FEATURE_AUTO_PRUNE",
    "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY",
]


def frontend_visible_config(config_dict):
    visible_dict = {}
    for name in CLIENT_WHITELIST:
        if name.lower().find("secret") >= 0:
            raise Exception("Cannot whitelist secrets: %s" % name)

        if name in config_dict:
            visible_dict[name] = config_dict.get(name, None)
        if "ENTERPRISE_LOGO_URL" in config_dict:
            visible_dict["BRANDING"] = visible_dict.get("BRANDING", {})
            visible_dict["BRANDING"]["logo"] = config_dict["ENTERPRISE_LOGO_URL"]

    return visible_dict


# Configuration that should not be changed by end users
class ImmutableConfig(object):
    # Requests based HTTP client with a large request pool
    HTTPCLIENT = build_requests_session()

    # Status tag config
    STATUS_TAGS = {}
    for tag_name in ["building", "failed", "none", "ready", "cancelled"]:
        tag_path = os.path.join(ROOT_DIR, "buildstatus", tag_name + ".svg")
        with open(tag_path) as tag_svg:
            STATUS_TAGS[tag_name] = tag_svg.read()

    # Reverse DNS prefixes that are reserved for internal use on labels and should not be allowable
    # to be set via the API.
    DEFAULT_LABEL_KEY_RESERVED_PREFIXES = [
        "com.docker.",
        "io.docker.",
        "org.dockerproject.",
        "org.opencontainers.",
        "io.cncf.",
        "io.kubernetes.",
        "io.k8s.",
        "io.quay",
        "com.coreos",
        "com.tectonic",
        "internal",
        "quay",
    ]

    # Colors for local avatars.
    AVATAR_COLORS = [
        "#969696",
        "#aec7e8",
        "#ff7f0e",
        "#ffbb78",
        "#2ca02c",
        "#98df8a",
        "#d62728",
        "#ff9896",
        "#9467bd",
        "#c5b0d5",
        "#8c564b",
        "#c49c94",
        "#e377c2",
        "#f7b6d2",
        "#7f7f7f",
        "#c7c7c7",
        "#bcbd22",
        "#1f77b4",
        "#17becf",
        "#9edae5",
        "#393b79",
        "#5254a3",
        "#6b6ecf",
        "#9c9ede",
        "#9ecae1",
        "#31a354",
        "#b5cf6b",
        "#a1d99b",
        "#8c6d31",
        "#ad494a",
        "#e7ba52",
        "#a55194",
    ]

    # Colors for channels.
    CHANNEL_COLORS = [
        "#969696",
        "#aec7e8",
        "#ff7f0e",
        "#ffbb78",
        "#2ca02c",
        "#98df8a",
        "#d62728",
        "#ff9896",
        "#9467bd",
        "#c5b0d5",
        "#8c564b",
        "#c49c94",
        "#e377c2",
        "#f7b6d2",
        "#7f7f7f",
        "#c7c7c7",
        "#bcbd22",
        "#1f77b4",
        "#17becf",
        "#9edae5",
        "#393b79",
        "#5254a3",
        "#6b6ecf",
        "#9c9ede",
        "#9ecae1",
        "#31a354",
        "#b5cf6b",
        "#a1d99b",
        "#8c6d31",
        "#ad494a",
        "#e7ba52",
        "#a55194",
    ]

    PROPAGATE_EXCEPTIONS = True


class DefaultConfig(ImmutableConfig):
    # Flask config
    JSONIFY_PRETTYPRINT_REGULAR = False
    SESSION_COOKIE_NAME = "_csrf_token"
    SESSION_COOKIE_SECURE = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    LOGGING_LEVEL = "DEBUG"
    SEND_FILE_MAX_AGE_DEFAULT = 0
    PREFERRED_URL_SCHEME = "http"
    SERVER_HOSTNAME = "localhost:5000"

    if os.environ.get("RED_HAT_QUAY", False):
        REGISTRY_TITLE = "Red Hat Quay"
        REGISTRY_TITLE_SHORT = "Red Hat Quay"
    else:
        REGISTRY_TITLE = "Project Quay"
        REGISTRY_TITLE_SHORT = "Project Quay"

    CONTACT_INFO: List[str] = []

    # Mail config
    MAIL_SERVER = ""
    MAIL_USE_TLS = True
    MAIL_PORT = 587
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_DEFAULT_SENDER = "admin@example.com"
    MAIL_FAIL_SILENTLY = False
    TESTING = True

    # DB config
    DB_URI = "sqlite:///test/data/test.db"
    DB_CONNECTION_ARGS: Optional[Dict[str, Any]] = {
        "threadlocals": True,
        "autorollback": True,
    }

    @staticmethod
    def create_transaction(db):
        # This hack is for handling possible MySQL closing idle connections.
        # Peewee/pymysql's will try to reuse the existing connection after the MySQL server
        # has already closed it, which will return an InterfaceError.
        # AFAIK, there isn't a way to actually test for a a stale connection without actually
        # running a query. Closing the connection before the transaction forces peewee/pymysql
        # to reopen a new session to MySQL. This should only applies to non-registry workers,
        # as the registry workers use a pool by default, and shouldn't have this issue.
        if type(db.obj).__name__ == "ObservableRetryingMySQLDatabase":
            try:
                db.close()
            except:
                # Only try to close the connection. Otherwise closing connections in a nested transaction
                # will return an OperationalError. In that case, we can just continue with the normal flow,
                # as we know the connection is likely in use and not stale.
                pass

        return db.transaction()

    DB_TRANSACTION_FACTORY = create_transaction

    # If set to 'readonly', the entire registry is placed into read only mode and no write operations
    # may be performed against it.
    REGISTRY_STATE = "normal"

    # If set to true, TLS is used, but is terminated by an external service (such as a load balancer).
    # Note that PREFERRED_URL_SCHEME must be `https` when this flag is set or it can lead to undefined
    # behavior.
    EXTERNAL_TLS_TERMINATION = False

    # If true, CDN URLs will be used for our external dependencies, rather than the local
    # copies.
    USE_CDN = False

    # Authentication
    AUTHENTICATION_TYPE = "Database"

    # Build logs
    BUILDLOGS_REDIS = {"host": "localhost"}
    BUILDLOGS_OPTIONS: List[Any] = []

    # Real-time user events
    USER_EVENTS_REDIS = {"host": "localhost"}

    # Stripe config
    BILLING_TYPE = "FakeStripe"

    # Analytics
    ANALYTICS_TYPE = "FakeAnalytics"

    # Build Queue Metrics
    QUEUE_METRICS_TYPE = "Null"
    QUEUE_WORKER_METRICS_REFRESH_SECONDS = 300

    # Exception logging
    EXCEPTION_LOG_TYPE = "FakeSentry"
    SENTRY_DSN = None
    SENTRY_PUBLIC_DSN = None

    # Github Config
    GITHUB_LOGIN_CONFIG: Optional[Dict[str, Any]] = None
    GITHUB_TRIGGER_CONFIG = None

    # Google Config.
    GOOGLE_LOGIN_CONFIG: Optional[Dict[str, str]] = None

    # Bitbucket Config.
    BITBUCKET_TRIGGER_CONFIG: Optional[Dict[str, str]] = None

    # Gitlab Config.
    GITLAB_TRIGGER_CONFIG: Optional[Dict[str, str]] = None

    NOTIFICATION_QUEUE_NAME = "notification"
    DOCKERFILE_BUILD_QUEUE_NAME = "dockerfilebuild"
    REPLICATION_QUEUE_NAME = "imagestoragereplication"
    CHUNK_CLEANUP_QUEUE_NAME = "chunk_cleanup"
    NAMESPACE_GC_QUEUE_NAME = "namespacegc"
    REPOSITORY_GC_QUEUE_NAME = "repositorygc"
    EXPORT_ACTION_LOGS_QUEUE_NAME = "exportactionlogs"
    SECSCAN_V4_NOTIFICATION_QUEUE_NAME = "secscanv4"

    # Super user config. Note: This MUST BE an empty list for the default config.
    SUPER_USERS: List[str] = []

    # Global readonly user.
    # WARNING: THIS WILL GIVE USERS OF THIS LIST READ ACCESS TO ALL REPOS,
    # REGARDLESS OF WHETHER THEY ARE PUBLIC OR NOT
    GLOBAL_READONLY_SUPER_USERS: List[str] = []

    # Feature Flag: Whether sessions are permanent.
    FEATURE_PERMANENT_SESSIONS = True

    # Feature Flag: Whether super users are supported.
    FEATURE_SUPER_USERS = True

    # Feature Flag: Whether to allow anonymous users to browse and pull public repositories.
    FEATURE_ANONYMOUS_ACCESS = True

    # Feature Flag: Whether billing is required.
    FEATURE_BILLING = False

    # Feature Flag: Whether user accounts automatically have usage log access.
    FEATURE_USER_LOG_ACCESS = False

    # Feature Flag: Whether GitHub login is supported.
    FEATURE_GITHUB_LOGIN = False

    # Feature Flag: Whether Google login is supported.
    FEATURE_GOOGLE_LOGIN = False

    # Feature Flag: Whether to support GitHub build triggers.
    FEATURE_GITHUB_BUILD = False

    # Feature Flag: Whether to support Bitbucket build triggers.
    FEATURE_BITBUCKET_BUILD = False

    # Feature Flag: Whether to support GitLab build triggers.
    FEATURE_GITLAB_BUILD = False

    # Feature Flag: Dockerfile build support.
    FEATURE_BUILD_SUPPORT = True

    # Feature Flag: Whether emails are enabled.
    FEATURE_MAILING = True

    # Feature Flag: Whether users can be created (by non-super users).
    FEATURE_USER_CREATION = True

    # Feature Flag: Whether users being created must be invited by another user.
    # If FEATURE_USER_CREATION is off, this flag has no effect.
    FEATURE_INVITE_ONLY_USER_CREATION = False

    # Feature Flag: Whether users can be renamed
    FEATURE_USER_RENAME = False

    # Feature Flag: Whether non-encrypted passwords (as opposed to encrypted tokens) can be used for
    # basic auth.
    FEATURE_REQUIRE_ENCRYPTED_BASIC_AUTH = False

    # Feature Flag: Whether to automatically replicate between storage engines.
    FEATURE_STORAGE_REPLICATION = False  # Optional[bool]

    # Feature Flag: Whether users can directly login to the UI.
    FEATURE_DIRECT_LOGIN = True

    # Feature Flag: Whether the v2/ endpoint is visible
    FEATURE_ADVERTISE_V2 = True

    # Semver spec for which Docker versions we will blacklist
    # Documentation: http://pythonhosted.org/semantic_version/reference.html#semantic_version.Spec
    BLACKLIST_V2_SPEC = "<1.6.0"

    # Feature Flag: Whether to restrict V1 pushes to the whitelist.
    FEATURE_RESTRICTED_V1_PUSH = False
    V1_PUSH_WHITELIST: Optional[List[str]] = []

    # Feature Flag: Whether or not to rotate old action logs to storage.
    FEATURE_ACTION_LOG_ROTATION = False

    # Feature Flag: Whether to allow for "namespace-less" repositories when pulling and pushing from
    # Docker.
    FEATURE_LIBRARY_SUPPORT = True

    # Feature Flag: Whether to require invitations when adding a user to a team.
    FEATURE_REQUIRE_TEAM_INVITE = True

    # Feature Flag: Whether to proxy all direct download URLs in storage via the registry's nginx.
    FEATURE_PROXY_STORAGE = False

    # Feature Flag: Whether to collect and support user metadata.
    FEATURE_USER_METADATA = False

    # Feature Flag: Whether to support signing
    FEATURE_SIGNING = False

    # Feature Flag: If set to true, the _catalog endpoint returns public repositories. Otherwise,
    # only private repositories can be returned.
    FEATURE_PUBLIC_CATALOG = False

    # Feature Flag: If set to true, build logs may be read by those with read access to the repo,
    # rather than only write access or admin access.
    FEATURE_READER_BUILD_LOGS = False

    # Feature Flag: If set to true, autocompletion will apply to partial usernames.
    FEATURE_PARTIAL_USER_AUTOCOMPLETE = True

    # Feature Flag: If set to true, users can confirm (and modify) their initial usernames when
    # logging in via OIDC or a non-database internal auth provider.
    FEATURE_USERNAME_CONFIRMATION = True

    # Feature Flag: If set to true, Quay will run using FIPS compliant hash functions.
    FEATURE_FIPS = False

    # If a namespace is defined in the public namespace list, then it will appear on *all*
    # user's repository list pages, regardless of whether that user is a member of the namespace.
    # Typically, this is used by an enterprise customer in configuring a set of "well-known"
    # namespaces.
    PUBLIC_NAMESPACES: List[str] = []

    # The namespace to use for library repositories.
    # Note: This must remain 'library' until Docker removes their hard-coded namespace for libraries.
    # See: https://github.com/docker/docker/blob/master/registry/session.go#L320
    LIBRARY_NAMESPACE = "library"

    BUILD_MANAGER: Tuple[str, Dict[Any, Any]] = ("enterprise", {})

    DISTRIBUTED_STORAGE_CONFIG: Optional[Dict[str, List[Any]]] = {
        "local_eu": ["LocalStorage", {"storage_path": "test/data/registry/eu"}],
        "local_us": ["LocalStorage", {"storage_path": "test/data/registry/us"}],
    }

    DISTRIBUTED_STORAGE_PREFERENCE = ["local_us"]
    DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS = ["local_us"]

    # Health checker.
    HEALTH_CHECKER: Tuple[str, Dict[Any, Any]] = ("LocalHealthCheck", {})

    # Userfiles
    USERFILES_LOCATION = "local_us"
    USERFILES_PATH = "userfiles/"

    # Build logs archive
    LOG_ARCHIVE_LOCATION = "local_us"
    LOG_ARCHIVE_PATH = "logarchive/"

    # Action logs configuration for advanced events
    ACTION_LOG_AUDIT_LOGINS = True

    # Action logs configuration for failure tracking
    ACTION_LOG_AUDIT_LOGIN_FAILURES = False
    ACTION_LOG_AUDIT_PULL_FAILURES = False
    ACTION_LOG_AUDIT_PUSH_FAILURES = False
    ACTION_LOG_AUDIT_DELETE_FAILURES = False

    # Action logs archive
    ACTION_LOG_ARCHIVE_LOCATION: Optional[str] = "local_us"
    ACTION_LOG_ARCHIVE_PATH: Optional[str] = "actionlogarchive/"
    ACTION_LOG_ROTATION_THRESHOLD = "30d"

    # Allow registry pulls when unable to write to the audit log
    ALLOW_PULLS_WITHOUT_STRICT_LOGGING = False

    # Allow any registry action when unable to write to the audit log
    ALLOW_WITHOUT_STRICT_LOGGING = False

    # Temporary tag expiration in seconds, this may actually be longer based on GC policy
    PUSH_TEMP_TAG_EXPIRATION_SEC = 60 * 60  # One hour per layer

    # Signed registry grant token expiration in seconds
    SIGNED_GRANT_EXPIRATION_SEC = 60 * 60 * 24  # One day to complete a push/pull

    # Registry v2 JWT Auth config
    REGISTRY_JWT_AUTH_MAX_FRESH_S = (
        60 * 60 + 60
    )  # At most signed one hour, accounting for clock skew

    # The URL endpoint to which we redirect OAuth when generating a token locally.
    LOCAL_OAUTH_HANDLER = "/oauth/localapp"

    # The various avatar background colors.
    AVATAR_KIND = "local"

    # Custom branding
    BRANDING: Dict[str, Optional[str]]
    if os.environ.get("RED_HAT_QUAY", False):
        BRANDING = {
            "logo": "/static/img/RH_Logo_Quay_Black_UX-horizontal.svg",
            "footer_img": "/static/img/RedHat.svg",
            "footer_url": "https://access.redhat.com/documentation/en-us/red_hat_quay/3/",
        }
    else:
        BRANDING = {
            "logo": "/static/img/quay-horizontal-color.svg",
            "footer_img": None,
            "footer_url": None,
        }

    # How often the Garbage Collection worker runs.
    GARBAGE_COLLECTION_FREQUENCY = 30  # seconds

    # How long notifications will try to send before timing out.
    NOTIFICATION_SEND_TIMEOUT = 10

    # Security scanner
    FEATURE_SECURITY_SCANNER = False
    FEATURE_SECURITY_NOTIFICATIONS = False

    # The endpoint for the V4 security scanner.
    SECURITY_SCANNER_V4_ENDPOINT: Optional[str] = None

    # Cleanup deleted manifests from the security scanner service.
    SECURITY_SCANNER_V4_MANIFEST_CLEANUP: Optional[bool] = True

    # The number of seconds between indexing intervals in the security scanner
    SECURITY_SCANNER_INDEXING_INTERVAL = 30

    # Minimum number of seconds before re-indexing a manifest with the security scanner.
    SECURITY_SCANNER_V4_REINDEX_THRESHOLD = 300

    # Maximum layer size allowed for indexing.
    SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE = None

    # A base64 encoded string used to sign JWT(s) on Clair V4
    # requests. If none jwt signing will not occur
    SECURITY_SCANNER_V4_PSK = None

    # Repository mirror
    FEATURE_REPO_MIRROR = False

    # The number of seconds between indexing intervals in the repository mirror
    REPO_MIRROR_INTERVAL = 30

    # Require HTTPS and verify certificates of Quay registry during mirror.
    REPO_MIRROR_TLS_VERIFY = True

    # Replaces the SERVER_HOSTNAME as the destination for mirroring.
    REPO_MIRROR_SERVER_HOSTNAME: Optional[str] = None

    # Enables rolling repository back to previous state in the event the mirror fails.
    # Defaults to false, to allow partial mirroring of upstream repositories.
    REPO_MIRROR_ROLLBACK = False

    # "Secret" key for generating encrypted paging tokens. Only needed to be secret to
    # hide the ID range for production (in which this value is overridden). Should *not*
    # be relied upon for secure encryption otherwise.
    # This value is a Fernet key and should be 32bytes URL-safe base64 encoded.
    PAGE_TOKEN_KEY = "0OYrc16oBuksR8T3JGB-xxYSlZ2-7I_zzqrLzggBJ58="

    # The timeout for service key approval.
    UNAPPROVED_SERVICE_KEY_TTL_SEC = 60 * 60 * 24  # One day

    # How long to wait before GCing an expired service key.
    EXPIRED_SERVICE_KEY_TTL_SEC = 60 * 60 * 24 * 7  # One week

    # The ID of the user account in the database to be used for service audit logs. If none, the
    # lowest user in the database will be used.
    SERVICE_LOG_ACCOUNT_ID = None

    # The service key ID for the instance service.
    INSTANCE_SERVICE_KEY_SERVICE = "quay"

    # The location of the key ID file generated for this instance.
    INSTANCE_SERVICE_KEY_KID_LOCATION = os.path.join(CONF_DIR, "quay.kid")

    # The location of the private key generated for this instance.
    INSTANCE_SERVICE_KEY_LOCATION = os.path.join(CONF_DIR, "quay.pem")

    # This instance's service key expiration in minutes.
    INSTANCE_SERVICE_KEY_EXPIRATION = 120

    # Number of minutes between expiration refresh in minutes. Should be the expiration / 2 minus
    # some additional window time.
    INSTANCE_SERVICE_KEY_REFRESH = 55

    # The whitelist of client IDs for OAuth applications that allow for direct login.
    DIRECT_OAUTH_CLIENTID_WHITELIST: Optional[List[str]] = []

    # URL that specifies the location of the prometheus pushgateway.
    PROMETHEUS_PUSHGATEWAY_URL: Optional[str] = "http://localhost:9091"

    # Namespace prefix for all prometheus metrics.
    PROMETHEUS_NAMESPACE = "quay"

    # Overridable list of reverse DNS prefixes that are reserved for internal use on labels.
    LABEL_KEY_RESERVED_PREFIXES: Optional[List[str]] = []

    # Delays workers from starting until a random point in time between 0 and their regular interval.
    STAGGER_WORKERS = True

    # Location of the static marketing site.
    STATIC_SITE_BUCKET = None

    # Site key and secret key for using recaptcha.
    FEATURE_RECAPTCHA = False
    RECAPTCHA_SITE_KEY: Optional[str] = None
    RECAPTCHA_SECRET_KEY: Optional[str] = None

    # List of users allowed to pass through recaptcha security check to enable org/user creation via API
    RECAPTCHA_WHITELISTED_USERS: List[str] = []

    # Server where TUF metadata can be found
    TUF_SERVER = None

    # Prefix to add to metadata e.g. <prefix>/<namespace>/<reponame>
    TUF_GUN_PREFIX = None

    # Maximum size allowed for layers in the registry.
    MAXIMUM_LAYER_SIZE = "20G"

    # Feature Flag: Whether team syncing from the backing auth is enabled.
    FEATURE_TEAM_SYNCING = False
    TEAM_RESYNC_STALE_TIME = "30m"
    TEAM_SYNC_WORKER_FREQUENCY = 60  # seconds

    # Feature Flag: If enabled, non-superusers can setup team syncing.
    FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP = False

    # The default configurable tag expiration time for time machine.
    DEFAULT_TAG_EXPIRATION = "2w"

    # The options to present in namespace settings for the tag expiration. If empty, no option
    # will be given and the default will be displayed read-only.
    TAG_EXPIRATION_OPTIONS = ["0s", "1d", "1w", "2w", "4w"]

    # Feature Flag: Whether users can view and change their tag expiration.
    FEATURE_CHANGE_TAG_EXPIRATION = True

    # Defines a secret for enabling the health-check endpoint's debug information.
    ENABLE_HEALTH_DEBUG_SECRET = None

    # The lifetime for a user recovery token before it becomes invalid.
    USER_RECOVERY_TOKEN_LIFETIME = "30m"

    # If specified, when app specific passwords expire by default.
    APP_SPECIFIC_TOKEN_EXPIRATION = None

    # Feature Flag: If enabled, users can create and use app specific tokens to login via the CLI.
    FEATURE_APP_SPECIFIC_TOKENS = True

    # How long expired app specific tokens should remain visible to users before being automatically
    # deleted. Set to None to turn off garbage collection.
    EXPIRED_APP_SPECIFIC_TOKEN_GC = "1d"

    # The size of pages returned by the Docker V2 API.
    V2_PAGINATION_SIZE = 50

    # If enabled, ensures that API calls are made with the X-Requested-With header
    # when called from a browser.
    BROWSER_API_CALLS_XHR_ONLY = True

    # If set to a non-None integer value, the default number of maximum builds for a namespace.
    DEFAULT_NAMESPACE_MAXIMUM_BUILD_COUNT: Optional[int] = None

    # If set to a non-None integer value, the default number of maximum builds for a namespace whose
    # creator IP is deemed a threat.
    THREAT_NAMESPACE_MAXIMUM_BUILD_COUNT: Optional[int] = None

    # The API Key to use when requesting IP information.
    IP_DATA_API_KEY = None

    # For Billing Support Only: The number of allowed builds on a namespace that has been billed
    # successfully.
    BILLED_NAMESPACE_MAXIMUM_BUILD_COUNT: Optional[int] = None

    # Configuration for the data model cache.
    DATA_MODEL_CACHE_CONFIG = {
        "engine": "memcached",
        "endpoint": ("127.0.0.1", 18080),
        "repository_blob_cache_ttl": "60s",
        "catalog_page_cache_ttl": "60s",
        "namespace_geo_restrictions_cache_ttl": "240s",
        "active_repo_tags_cache_ttl": "120s",
        "value_size_limit": "1MiB",
    }

    # Defines the number of successive failures of a build trigger's build before the trigger is
    # automatically disabled.
    SUCCESSIVE_TRIGGER_FAILURE_DISABLE_THRESHOLD = 100

    # Defines the number of successive internal errors of a build trigger's build before the
    # trigger is automatically disabled.
    SUCCESSIVE_TRIGGER_INTERNAL_ERROR_DISABLE_THRESHOLD = 5

    # Defines the delay required (in seconds) before the last_accessed field of a user/robot or access
    # token will be updated after the previous update.
    LAST_ACCESSED_UPDATE_THRESHOLD_S = 60

    # Defines the number of results per page used to show search results
    SEARCH_RESULTS_PER_PAGE = 10

    # Defines the maximum number of pages the user can paginate before they are limited
    SEARCH_MAX_RESULT_PAGE_COUNT = 10

    # Feature Flag: Whether to record when users were last accessed.
    FEATURE_USER_LAST_ACCESSED = True

    # Feature Flag: Whether to allow users to retrieve aggregated log counts.
    FEATURE_AGGREGATED_LOG_COUNT_RETRIEVAL = True

    # Feature Flag: Whether rate limiting is enabled.
    FEATURE_RATE_LIMITS = False

    # Feature Flag: Whether to support log exporting.
    FEATURE_LOG_EXPORT = True

    # Maximum number of action logs pages that can be returned via the API.
    ACTION_LOG_MAX_PAGE = None

    # Log model
    LOGS_MODEL = "database"
    LOGS_MODEL_CONFIG: Dict[str, Any] = {}

    # Namespace in which all audit logging is disabled.
    DISABLED_FOR_AUDIT_LOGS: List[str] = []

    # Namespace in which pull audit logging is disabled.
    DISABLED_FOR_PULL_LOGS: List[str] = []

    # Feature Flag: Whether pull logs are disabled for free namespace.
    FEATURE_DISABLE_PULL_LOGS_FOR_FREE_NAMESPACES = False

    # Feature Flag: If set to true, no account using blacklisted email addresses will be allowed
    # to be created.
    FEATURE_BLACKLISTED_EMAILS = False

    # The list of domains, including subdomains, for which any *new* User with a matching
    # email address will be denied creation. This option is only used if
    # FEATURE_BLACKLISTED_EMAILS is enabled.
    BLACKLISTED_EMAIL_DOMAINS: List[str] = []

    # Feature Flag: Whether garbage collection is enabled.
    FEATURE_GARBAGE_COLLECTION = True

    # Feature Flags: Whether the workers for GCing deleted namespaces and repositories
    # are enabled.
    FEATURE_NAMESPACE_GARBAGE_COLLECTION = True
    FEATURE_REPOSITORY_GARBAGE_COLLECTION = True

    # When enabled, sets a tracing callback to report greenlet metrics.
    GREENLET_TRACING = True

    # The timeout after which a fresh login check is required for sensitive operations.
    FRESH_LOGIN_TIMEOUT = "10m"

    # Feature Flag: Whether to clear expired RepositoryActionCount entries.
    FEATURE_CLEAR_EXPIRED_RAC_ENTRIES = False

    # Feature Flag: Whether OCI manifest support should be enabled generally.
    FEATURE_GENERAL_OCI_SUPPORT = True
    ALLOWED_OCI_ARTIFACT_TYPES = {
        "application/vnd.oci.image.config.v1+json": [
            "application/vnd.dev.cosign.simplesigning.v1+json",
            "application/vnd.dsse.envelope.v1+json",
            "text/spdx",
            "text/spdx+xml",
            "text/spdx+json",
            "application/vnd.syft+json",
            "application/vnd.cyclonedx",
            "application/vnd.cyclonedx+xml",
            "application/vnd.cyclonedx+json",
            "application/vnd.in-toto+json",
        ],
        "application/vnd.cncf.helm.config.v1+json": [
            "application/tar+gzip",
            "application/vnd.cncf.helm.chart.content.v1.tar+gzip",
        ],
        "application/vnd.oci.source.image.config.v1+json": [
            "application/vnd.oci.image.layer.v1.tar+gzip"
        ],
        "application/vnd.unknown.config.v1+json": [
            "application/vnd.cncf.openpolicyagent.policy.layer.v1+rego",
            "application/vnd.cncf.openpolicyagent.data.layer.v1+json",
        ],
    }

    # Feature Flag: Whether to allow Helm OCI content types.
    # See: https://helm.sh/docs/topics/registries/
    FEATURE_HELM_OCI_SUPPORT = True

    FEATURE_REFERRERS_API = True

    # The set of hostnames disallowed from webhooks, beyond localhost (which will
    # not work due to running inside a container).
    WEBHOOK_HOSTNAME_BLACKLIST: Optional[List[str]] = []

    # The root URL for documentation.
    if os.environ.get("RED_HAT_QUAY", False):
        DOCUMENTATION_ROOT = "https://access.redhat.com/documentation/en-us/red_hat_quay/3/"
    else:
        DOCUMENTATION_ROOT = "https://docs.projectquay.io/"

    # Feature Flag: Whether the repository action count worker is enabled.
    FEATURE_REPOSITORY_ACTION_COUNTER = True

    # TEMP FEATURE: Backfill the sizes and subjects of manifests.
    FEATURE_MANIFEST_SIZE_BACKFILL = True
    FEATURE_MANIFEST_SUBJECT_BACKFILL = True

    # Repos created by push default to private visibility
    CREATE_PRIVATE_REPO_ON_PUSH = True

    # Create organization on push if it does not exist
    CREATE_NAMESPACE_ON_PUSH = False

    # Account recovery mode
    ACCOUNT_RECOVERY_MODE = False

    # Feature Flag: If set to true, the first User account may be created via API /api/v1/user/initialize
    FEATURE_USER_INITIALIZE = False

    # Allows "/" in repository names
    FEATURE_EXTENDED_REPOSITORY_NAMES = True

    # Automatically clean stale blobs leftover in the uploads storage folder from cancelled uploads
    CLEAN_BLOB_UPLOAD_FOLDER = True

    # Add quota management configuration, caching, and validation
    FEATURE_QUOTA_MANAGEMENT = False

    FEATURE_EDIT_QUOTA = True

    # Enables quota verfication on image push
    FEATURE_VERIFY_QUOTA = True

    # Catches and suppresses quota failures during image push and garbage collection
    FEATURE_QUOTA_SUPPRESS_FAILURES = False

    # default value for all organizations to reject by default. 0 = no configuration
    DEFAULT_SYSTEM_REJECT_QUOTA_BYTES = 0
    # Time delay for starting the quota backfill. Rolling deployments can cause incorrect
    # totals, so this field should be set to a time longer than it takes for the rolling
    # deployment to complete. Defaults to 30m.
    QUOTA_TOTAL_DELAY_SECONDS = 60 * 30

    # Enables the quota backfill worker
    QUOTA_BACKFILL = True

    # Feature Flag: Enables Quay to act as a pull through cache for upstream registries
    FEATURE_PROXY_CACHE = False

    # Feature Flag: Use Red Hat Export Compliance Service during Red Hat SSO (only used in Quay.io)
    FEATURE_EXPORT_COMPLIANCE = False

    # Feature Flag: Enables user to try the beta UI Environment
    FEATURE_UI_V2 = False

    # User feedback form for UI-V2
    UI_V2_FEEDBACK_FORM = "https://7qdvkuo9rkj.typeform.com/to/XH5YE79P"

    # Export Compliance Endpoint
    EXPORT_COMPLIANCE_ENDPOINT = ""

    # Origin to allow for CORS requests
    CORS_ORIGIN = "*"

    # Feature Flag: Enables notifications about vulnerabilities to be sent for new pushes
    FEATURE_SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX = True

    # Set minimal security level for new notifications on detected vulnerabilities. Avoids
    # creation of large number of notifications after first index. If not defined, defaults to "High".
    NOTIFICATION_MIN_SEVERITY_ON_NEW_INDEX = "High"

    FEATURE_SUPERUSERS_FULL_ACCESS = False
    FEATURE_SUPERUSERS_ORG_CREATION_ONLY = False

    FEATURE_RESTRICTED_USERS = False
    RESTRICTED_USERS_WHITELIST: Optional[List[str]] = None

    QUOTA_INVALIDATE_TOTALS = True
    RESET_CHILD_MANIFEST_EXPIRATION = False
    PERMANENTLY_DELETE_TAGS = False

    # Feature Flag: Enables reconciler for RH marketplace
    FEATURE_ENTITLEMENT_RECONCILIATION = False
    # Endpoints for marketplace compatibility
    ENTITLEMENT_RECONCILIATION_USER_ENDPOINT = ""
    ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT = ""

    FEATURE_RH_MARKETPLACE = False

    # Set up custom TOS for on-premise installations
    TERMS_OF_SERVICE_URL = ""

    FEATURE_AUTO_PRUNE = False
    # delay after a write operation is made to the DB. This
    # is useful if quay is using a different DB for reads and
    # there is a delay in replication

    FEATURE_UI_DELAY_AFTER_WRITE = False
    UI_DELAY_AFTER_WRITE_SECONDS = 3

    # whitelist for ROBOTS_DISALLOW to grant access/usage for mirroring
    ROBOTS_WHITELIST: Optional[List[str]] = []

    FEATURE_ASSIGN_OAUTH_TOKEN = True
    DEFAULT_NAMESPACE_AUTOPRUNE_POLICY: Optional[Dict[str, str]] = None

    # Allows users to set up notifications on image expiry, can remove flag once feature is tested
    FEATURE_IMAGE_EXPIRY_TRIGGER = False

    # Disable pushes while allowing other registry operations.
    # Defaults to "False".
    DISABLE_PUSHES = False

    # Specific namespaces that be exceptions to the s3-cloudflare optimization
    # used for registry-proxy namespaces
    CDN_SPECIFIC_NAMESPACES: Optional[List[str]] = []
