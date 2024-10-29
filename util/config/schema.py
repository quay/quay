# INTERNAL_ONLY_PROPERTIES defines the properties in the config that, while settable, should
# not be documented for external users. These will generally be used for internal test or only
# given to customers when they have been briefed on the side effects of using them.
INTERNAL_ONLY_PROPERTIES = {
    "__module__",
    "__doc__",
    "__annotations__",
    "create_transaction",
    "SESSION_COOKIE_NAME",
    "SESSION_COOKIE_HTTPONLY",
    "SESSION_COOKIE_SAMESITE",
    "DATABASE_SECRET_KEY",
    "V22_NAMESPACE_BLACKLIST",
    "OCI_NAMESPACE_WHITELIST",
    "FEATURE_GENERAL_OCI_SUPPORT",
    "FEATURE_HELM_OCI_SUPPORT",
    "FEATURE_NAMESPACE_GARBAGE_COLLECTION",
    "FEATURE_REPOSITORY_GARBAGE_COLLECTION",
    "FEATURE_REPOSITORY_ACTION_COUNTER",
    "FEATURE_MANIFEST_SIZE_BACKFILL",
    "TESTING",
    "SEND_FILE_MAX_AGE_DEFAULT",
    "DISABLED_FOR_AUDIT_LOGS",
    "DISABLED_FOR_PULL_LOGS",
    "FEATURE_DISABLE_PULL_LOGS_FOR_FREE_NAMESPACES",
    "FEATURE_CLEAR_EXPIRED_RAC_ENTRIES",
    "ACTION_LOG_MAX_PAGE",
    "NON_RATE_LIMITED_NAMESPACES",
    "REPLICATION_QUEUE_NAME",
    "DOCKERFILE_BUILD_QUEUE_NAME",
    "CHUNK_CLEANUP_QUEUE_NAME",
    "NOTIFICATION_QUEUE_NAME",
    "REPOSITORY_GC_QUEUE_NAME",
    "NAMESPACE_GC_QUEUE_NAME",
    "EXPORT_ACTION_LOGS_QUEUE_NAME",
    "SECSCAN_V4_NOTIFICATION_QUEUE_NAME",
    "FEATURE_BILLING",
    "BILLING_TYPE",
    "INSTANCE_SERVICE_KEY_LOCATION",
    "INSTANCE_SERVICE_KEY_REFRESH",
    "INSTANCE_SERVICE_KEY_SERVICE",
    "INSTANCE_SERVICE_KEY_KID_LOCATION",
    "INSTANCE_SERVICE_KEY_EXPIRATION",
    "UNAPPROVED_SERVICE_KEY_TTL_SEC",
    "EXPIRED_SERVICE_KEY_TTL_SEC",
    "REGISTRY_JWT_AUTH_MAX_FRESH_S",
    "SERVICE_LOG_ACCOUNT_ID",
    "BUILDLOGS_OPTIONS",
    "LIBRARY_NAMESPACE",
    "STAGGER_WORKERS",
    "QUEUE_WORKER_METRICS_REFRESH_SECONDS",
    "PUSH_TEMP_TAG_EXPIRATION_SEC",
    "GARBAGE_COLLECTION_FREQUENCY",
    "PAGE_TOKEN_KEY",
    "BUILD_MANAGER",
    "SECURITY_SCANNER_V4_REINDEX_THRESHOLD",
    "STATIC_SITE_BUCKET",
    "LABEL_KEY_RESERVED_PREFIXES",
    "TEAM_SYNC_WORKER_FREQUENCY",
    "JSONIFY_PRETTYPRINT_REGULAR",
    "TUF_GUN_PREFIX",
    "LOGGING_LEVEL",
    "SIGNED_GRANT_EXPIRATION_SEC",
    "PROMETHEUS_PUSHGATEWAY_URL",
    "DB_TRANSACTION_FACTORY",
    "NOTIFICATION_SEND_TIMEOUT",
    "QUEUE_METRICS_TYPE",
    "MAIL_FAIL_SILENTLY",
    "LOCAL_OAUTH_HANDLER",
    "USE_CDN",
    "ANALYTICS_TYPE",
    "LAST_ACCESSED_UPDATE_THRESHOLD_S",
    "GREENLET_TRACING",
    "EXCEPTION_LOG_TYPE",
    "SENTRY_DSN",
    "SENTRY_PUBLIC_DSN",
    "BILLED_NAMESPACE_MAXIMUM_BUILD_COUNT",
    "THREAT_NAMESPACE_MAXIMUM_BUILD_COUNT",
    "IP_DATA_API_KEY",
    "REPO_MIRROR_INTERVAL",
    "DATA_MODEL_CACHE_CONFIG",
    # TODO: move this into the schema once we support signing in QE.
    "FEATURE_SIGNING",
    "TUF_SERVER",
    "V1_ONLY_DOMAIN",
    "LOGS_MODEL",
    "LOGS_MODEL_CONFIG",
    "V3_UPGRADE_MODE",  # Deprecated old flag
    "ACCOUNT_RECOVERY_MODE",
    "BLOBUPLOAD_DELETION_DATE_THRESHOLD",
    "REPO_MIRROR_TAG_ROLLBACK_PAGE_SIZE",
    "QUOTA_INVALIDATE_TOTALS",
    "RESET_CHILD_MANIFEST_EXPIRATION",
    "PERMANENTLY_DELETE_TAGS",
    "FEATURE_RH_MARKETPLACE",
    "CDN_SPECIFIC_NAMESPACES",
}

CONFIG_SCHEMA = {
    "type": "object",
    "description": "Schema for Quay configuration",
    "required": [
        "PREFERRED_URL_SCHEME",
        "SERVER_HOSTNAME",
        "DB_URI",
        "AUTHENTICATION_TYPE",
        "DISTRIBUTED_STORAGE_CONFIG",
        "BUILDLOGS_REDIS",
        "USER_EVENTS_REDIS",
        "DISTRIBUTED_STORAGE_PREFERENCE",
        "DEFAULT_TAG_EXPIRATION",
        "TAG_EXPIRATION_OPTIONS",
    ],
    "properties": {
        "REGISTRY_STATE": {
            "type": "string",
            "description": "The state of the registry.",
            "enum": ["normal", "readonly"],
            "x-example": "readonly",
        },
        # Hosting.
        "PREFERRED_URL_SCHEME": {
            "type": "string",
            "description": "The URL scheme to use when hitting Quay. If Quay is behind SSL *at all*, this *must* be `https`",
            "enum": ["http", "https"],
            "x-example": "https",
        },
        "SERVER_HOSTNAME": {
            "type": "string",
            "description": "The URL at which Quay is accessible, without the scheme.",
            "x-example": "quay.io",
        },
        "EXTERNAL_TLS_TERMINATION": {
            "type": "boolean",
            "description": "If TLS is supported, but terminated at a layer before Quay, must be true.",
            "x-example": True,
        },
        # SSL/TLS.
        "SSL_CIPHERS": {
            "type": "array",
            "description": "If specified, the nginx-defined list of SSL ciphers to enabled and disabled",
            "x-example": ["CAMELLIA", "!3DES"],
            "x-reference": "http://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_ciphers",
        },
        "SSL_PROTOCOLS": {
            "type": "array",
            "description": "If specified, the nginx-defined list of SSL protocols to enabled and disabled",
            "x-example": ["TLSv1.1", "TLSv1.2"],
            "x-reference": "http://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_protocols",
        },
        # User-visible configuration.
        "REGISTRY_TITLE": {
            "type": "string",
            "description": "If specified, the long-form title for the registry. Defaults to `Red Hat Quay`.",
            "x-example": "Corp Container Service",
        },
        "REGISTRY_TITLE_SHORT": {
            "type": "string",
            "description": "If specified, the short-form title for the registry. Defaults to `Red Hat Quay`.",
            "x-example": "CCS",
        },
        "CONTACT_INFO": {
            "type": "array",
            "uniqueItems": True,
            "description": "If specified, contact information to display on the contact page. "
            + "If only a single piece of contact information is specified, the contact footer will link directly.",
            "items": [
                {
                    "type": "string",
                    "pattern": "^mailto:(.)+$",
                    "x-example": "mailto:admin@example.com",
                    "description": "Adds a link to send an e-mail",
                },
                {
                    "type": "string",
                    "pattern": "^irc://(.)+$",
                    "x-example": "irc://irc.libera.chat:6667/quay",
                    "description": "Adds a link to visit an IRC chat room",
                },
                {
                    "type": "string",
                    "pattern": "^tel:(.)+$",
                    "x-example": "tel:+1-888-930-3475",
                    "description": "Adds a link to call a phone number",
                },
                {
                    "type": "string",
                    "pattern": "^http(s)?://(.)+$",
                    "x-example": "https://twitter.com/quayio",
                    "description": "Adds a link to a defined URL",
                },
            ],
        },
        "SEARCH_RESULTS_PER_PAGE": {
            "type": "number",
            "description": "Number of results returned per page by search page. Defaults to 10",
            "x-example": 10,
        },
        "SEARCH_MAX_RESULT_PAGE_COUNT": {
            "type": "number",
            "description": "Maximum number of pages the user can paginate in search before they are limited. Defaults to 10",
            "x-example": 10,
        },
        # E-mail.
        "FEATURE_MAILING": {
            "type": "boolean",
            "description": "Whether emails are enabled. Defaults to True",
            "x-example": True,
        },
        "MAIL_SERVER": {
            "type": "string",
            "description": "The SMTP server to use for sending e-mails. Only required if FEATURE_MAILING is set to true.",
            "x-example": "smtp.somedomain.com",
        },
        "MAIL_USE_TLS": {
            "type": "boolean",
            "description": "If specified, whether to use TLS for sending e-mails.",
            "x-example": True,
        },
        "MAIL_PORT": {
            "type": "number",
            "description": "The SMTP port to use. If not specified, defaults to 587.",
            "x-example": 588,
        },
        "MAIL_USERNAME": {
            "type": ["string", "null"],
            "description": "The SMTP username to use when sending e-mails.",
            "x-example": "myuser",
        },
        "MAIL_PASSWORD": {
            "type": ["string", "null"],
            "description": "The SMTP password to use when sending e-mails.",
            "x-example": "mypassword",
        },
        "MAIL_DEFAULT_SENDER": {
            "type": ["string", "null"],
            "description": "If specified, the e-mail address used as the `from` when Quay sends e-mails. If none, defaults to `admin@example.com`.",
            "x-example": "support@myco.com",
        },
        # Database.
        "DB_URI": {
            "type": "string",
            "description": "The URI at which to access the database, including any credentials.",
            "x-example": "mysql+pymysql://username:password@dns.of.database/quay",
            "x-reference": "https://www.postgresql.org/docs/9.3/static/libpq-connect.html#AEN39495",
        },
        "DB_CONNECTION_ARGS": {
            "type": "object",
            "description": "If specified, connection arguments for the database such as timeouts and SSL.",
            "properties": {
                "threadlocals": {
                    "type": "boolean",
                    "description": "Whether to use thread-local connections. Should *ALWAYS* be `true`",
                },
                "autorollback": {
                    "type": "boolean",
                    "description": "Whether to use auto-rollback connections. Should *ALWAYS* be `true`",
                },
                "ssl": {
                    "type": "object",
                    "description": "SSL connection configuration",
                    "properties": {
                        "ca": {
                            "type": "string",
                            "description": "*Absolute container path* to the CA certificate to use for SSL connections",
                            "x-example": "conf/stack/ssl-ca-cert.pem",
                        },
                    },
                    "required": ["ca"],
                },
            },
            "required": ["threadlocals", "autorollback"],
        },
        "DB_CONNECTION_POOLING": {"type": "boolean", "description": "Allow pooling for DB"},
        "ALLOW_PULLS_WITHOUT_STRICT_LOGGING": {
            "type": "boolean",
            "description": "If true, pulls in which the pull audit log entry cannot be written will "
            + "still succeed. Useful if the database can fallback into a read-only state "
            + "and it is desired for pulls to continue during that time. Defaults to False.",
            "x-example": True,
        },
        "ALLOW_WITHOUT_STRICT_LOGGING": {
            "type": "boolean",
            "description": "If true, any action in which the audit log entry cannot be written will "
            + "still succeed. Useful if using an external logging service that may be down "
            + "intermittently and the registry should continue to work. Defaults to False.",
            "x-example": False,
        },
        # Storage.
        "FEATURE_STORAGE_REPLICATION": {
            "type": "boolean",
            "description": "Whether to automatically replicate between storage engines. Defaults to False",
            "x-example": False,
        },
        "FEATURE_PROXY_STORAGE": {
            "type": "boolean",
            "description": "Whether to proxy all direct download URLs in storage via the registry nginx. Defaults to False",
            "x-example": False,
        },
        "FEATURE_PROXY_CACHE": {
            "type": "boolean",
            "description": "Whether pull through proxy cache feature is enabled. Defaults to False",
            "x-example": False,
        },
        "MAXIMUM_LAYER_SIZE": {
            "type": "string",
            "description": "Maximum allowed size of an image layer. Defaults to 20G",
            "x-example": "100G",
            "pattern": "^[0-9]+(G|M)$",
        },
        "DISTRIBUTED_STORAGE_CONFIG": {
            "type": "object",
            "description": "Configuration for storage engine(s) to use in Quay. Each key is a unique ID"
            + " for a storage engine, with the value being a tuple of the type and "
            + " configuration for that engine.",
            "x-example": {
                "local_storage": ["LocalStorage", {"storage_path": "some/path/"}],
            },
            "items": {
                "type": "array",
            },
        },
        "DISTRIBUTED_STORAGE_PREFERENCE": {
            "type": "array",
            "description": "The preferred storage engine(s) (by ID in DISTRIBUTED_STORAGE_CONFIG) to "
            + "use. A preferred engine means it is first checked for pullig and images are "
            + "pushed to it.",
            "items": {
                "type": "string",
                "uniqueItems": True,
            },
            "x-example": ["s3_us_east", "s3_us_west"],
        },
        "DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS": {
            "type": "array",
            "description": "The list of storage engine(s) (by ID in DISTRIBUTED_STORAGE_CONFIG) whose "
            + "images should be fully replicated, by default, to all other storage engines.",
            "items": {
                "type": "string",
                "uniqueItems": True,
            },
            "x-example": ["s3_us_east", "s3_us_west"],
        },
        "USERFILES_LOCATION": {
            "type": "string",
            "description": "ID of the storage engine in which to place user-uploaded files",
            "x-example": "s3_us_east",
        },
        "USERFILES_PATH": {
            "type": "string",
            "description": "Path under storage in which to place user-uploaded files",
            "x-example": "userfiles",
        },
        "ACTION_LOG_AUDIT_LOGINS": {
            "type": "string",
            "description": "Whether to log all registry API and Quay API/UI logins event to the action log. Defaults to True",
            "x-example": False,
        },
        "ACTION_LOG_AUDIT_LOGIN_FAILURES": {
            "type": "boolean",
            "description": "Whether logging of failed logins attempts is enabled. Defaults to False",
            "x-example": True,
        },
        "ACTION_LOG_AUDIT_PULL_FAILURES": {
            "type": "boolean",
            "description": "Whether logging of failed image pull attempts is enabled. Defaults to False",
            "x-example": True,
        },
        "ACTION_LOG_AUDIT_PUSH_FAILURES": {
            "type": "boolean",
            "description": "Whether logging of failed image push attempts is enabled. Defaults to False",
            "x-example": True,
        },
        "ACTION_LOG_AUDIT_DELETE_FAILURES": {
            "type": "boolean",
            "description": "Whether logging of failed image delete attempts is enabled. Defaults to False",
            "x-example": True,
        },
        "ACTION_LOG_ARCHIVE_LOCATION": {
            "type": "string",
            "description": "If action log archiving is enabled, the storage engine in which to place the "
            + "archived data.",
            "x-example": "s3_us_east",
        },
        "ACTION_LOG_ARCHIVE_PATH": {
            "type": "string",
            "description": "If action log archiving is enabled, the path in storage in which to place the "
            + "archived data.",
            "x-example": "archives/actionlogs",
        },
        "ACTION_LOG_ROTATION_THRESHOLD": {
            "type": "string",
            "description": "If action log archiving is enabled, the time interval after which to "
            + "archive data.",
            "x-example": "30d",
        },
        "LOG_ARCHIVE_LOCATION": {
            "type": "string",
            "description": "If builds are enabled, the storage engine in which to place the "
            + "archived build logs.",
            "x-example": "s3_us_east",
        },
        "LOG_ARCHIVE_PATH": {
            "type": "string",
            "description": "If builds are enabled, the path in storage in which to place the "
            + "archived build logs.",
            "x-example": "archives/buildlogs",
        },
        # Authentication.
        "AUTHENTICATION_TYPE": {
            "type": "string",
            "description": "The authentication engine to use for credential authentication.",
            "x-example": "Database",
            "enum": ["Database", "LDAP", "JWT", "Keystone", "OIDC", "AppToken"],
        },
        "SUPER_USERS": {
            "type": "array",
            "description": "Quay usernames of those users to be granted superuser privileges",
            "uniqueItems": True,
            "items": {
                "type": "string",
            },
        },
        "DIRECT_OAUTH_CLIENTID_WHITELIST": {
            "type": "array",
            "description": "A list of client IDs of *Quay-managed* applications that are allowed "
            + "to perform direct OAuth approval without user approval.",
            "x-reference": "https://coreos.com/quay-enterprise/docs/latest/direct-oauth.html",
            "uniqueItems": True,
            "items": {
                "type": "string",
            },
        },
        # Redis.
        "BUILDLOGS_REDIS": {
            "type": "object",
            "description": "Connection information for Redis for build logs caching",
            "required": ["host"],
            "properties": {
                "host": {
                    "type": "string",
                    "description": "The hostname at which Redis is accessible",
                    "x-example": "my.redis.cluster",
                },
                "port": {
                    "type": "number",
                    "description": "The port at which Redis is accessible",
                    "x-example": 1234,
                },
                "password": {
                    "type": "string",
                    "description": "The password to connect to the Redis instance",
                    "x-example": "mypassword",
                },
            },
        },
        "USER_EVENTS_REDIS": {
            "type": "object",
            "description": "Connection information for Redis for user event handling",
            "required": ["host"],
            "properties": {
                "host": {
                    "type": "string",
                    "description": "The hostname at which Redis is accessible",
                    "x-example": "my.redis.cluster",
                },
                "port": {
                    "type": "number",
                    "description": "The port at which Redis is accessible",
                    "x-example": 1234,
                },
                "password": {
                    "type": "string",
                    "description": "The password to connect to the Redis instance",
                    "x-example": "mypassword",
                },
            },
        },
        # OAuth configuration.
        "GITHUB_LOGIN_CONFIG": {
            "type": ["object", "null"],
            "description": "Configuration for using GitHub (Enterprise) as an external login provider",
            "required": ["CLIENT_ID", "CLIENT_SECRET"],
            "x-reference": "https://coreos.com/quay-enterprise/docs/latest/github-auth.html",
            "properties": {
                "GITHUB_ENDPOINT": {
                    "type": "string",
                    "description": "The endpoint of the GitHub (Enterprise) being hit",
                    "x-example": "https://github.com/",
                },
                "API_ENDPOINT": {
                    "type": "string",
                    "description": "The endpoint of the GitHub (Enterprise) API to use. Must be overridden for github.com",
                    "x-example": "https://api.github.com/",
                },
                "CLIENT_ID": {
                    "type": "string",
                    "description": "The registered client ID for this Quay instance; cannot be shared with GITHUB_TRIGGER_CONFIG",
                    "x-example": "0e8dbe15c4c7630b6780",
                    "x-reference": "https://coreos.com/quay-enterprise/docs/latest/github-app.html",
                },
                "CLIENT_SECRET": {
                    "type": "string",
                    "description": "The registered client secret for this Quay instance",
                    "x-example": "e4a58ddd3d7408b7aec109e85564a0d153d3e846",
                    "x-reference": "https://coreos.com/quay-enterprise/docs/latest/github-app.html",
                },
                "ORG_RESTRICT": {
                    "type": "boolean",
                    "description": "If true, only users within the organization whitelist can login using this provider",
                    "x-example": True,
                },
                "ALLOWED_ORGANIZATIONS": {
                    "type": "array",
                    "description": "The names of the GitHub (Enterprise) organizations whitelisted to work with the ORG_RESTRICT option",
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                    },
                },
            },
        },
        "BITBUCKET_TRIGGER_CONFIG": {
            "type": ["object", "null"],
            "description": "Configuration for using BitBucket for build triggers",
            "required": ["CONSUMER_KEY", "CONSUMER_SECRET"],
            "x-reference": "https://coreos.com/quay-enterprise/docs/latest/bitbucket-build.html",
            "properties": {
                "CONSUMER_KEY": {
                    "type": "string",
                    "description": "The registered consumer key (client ID) for this Quay instance",
                    "x-example": "0e8dbe15c4c7630b6780",
                },
                "CONSUMER_SECRET": {
                    "type": "string",
                    "description": "The registered consumer secret (client secret) for this Quay instance",
                    "x-example": "e4a58ddd3d7408b7aec109e85564a0d153d3e846",
                },
            },
        },
        "GITHUB_TRIGGER_CONFIG": {
            "type": ["object", "null"],
            "description": "Configuration for using GitHub (Enterprise) for build triggers",
            "required": ["GITHUB_ENDPOINT", "CLIENT_ID", "CLIENT_SECRET"],
            "x-reference": "https://coreos.com/quay-enterprise/docs/latest/github-build.html",
            "properties": {
                "GITHUB_ENDPOINT": {
                    "type": "string",
                    "description": "The endpoint of the GitHub (Enterprise) being hit",
                    "x-example": "https://github.com/",
                },
                "API_ENDPOINT": {
                    "type": "string",
                    "description": "The endpoint of the GitHub (Enterprise) API to use. Must be overridden for github.com",
                    "x-example": "https://api.github.com/",
                },
                "CLIENT_ID": {
                    "type": "string",
                    "description": "The registered client ID for this Quay instance; cannot be shared with GITHUB_LOGIN_CONFIG",
                    "x-example": "0e8dbe15c4c7630b6780",
                    "x-reference": "https://coreos.com/quay-enterprise/docs/latest/github-app.html",
                },
                "CLIENT_SECRET": {
                    "type": "string",
                    "description": "The registered client secret for this Quay instance",
                    "x-example": "e4a58ddd3d7408b7aec109e85564a0d153d3e846",
                    "x-reference": "https://coreos.com/quay-enterprise/docs/latest/github-app.html",
                },
            },
        },
        "GOOGLE_LOGIN_CONFIG": {
            "type": ["object", "null"],
            "description": "Configuration for using Google for external authentication",
            "required": ["CLIENT_ID", "CLIENT_SECRET"],
            "properties": {
                "CLIENT_ID": {
                    "type": "string",
                    "description": "The registered client ID for this Quay instance",
                    "x-example": "0e8dbe15c4c7630b6780",
                },
                "CLIENT_SECRET": {
                    "type": "string",
                    "description": "The registered client secret for this Quay instance",
                    "x-example": "e4a58ddd3d7408b7aec109e85564a0d153d3e846",
                },
            },
        },
        "GITLAB_TRIGGER_CONFIG": {
            "type": ["object", "null"],
            "description": "Configuration for using Gitlab (Enterprise) for external authentication",
            "required": ["GITLAB_ENDPOINT", "CLIENT_ID", "CLIENT_SECRET"],
            "properties": {
                "GITLAB_ENDPOINT": {
                    "type": "string",
                    "description": "The endpoint at which Gitlab(Enterprise) is running",
                    "x-example": "https://gitlab.com",
                },
                "CLIENT_ID": {
                    "type": "string",
                    "description": "The registered client ID for this Quay instance",
                    "x-example": "0e8dbe15c4c7630b6780",
                },
                "CLIENT_SECRET": {
                    "type": "string",
                    "description": "The registered client secret for this Quay instance",
                    "x-example": "e4a58ddd3d7408b7aec109e85564a0d153d3e846",
                },
            },
        },
        "BRANDING": {
            "type": ["object", "null"],
            "description": "Custom branding for logos and URLs in the Quay UI",
            "required": ["logo"],
            "properties": {
                "logo": {
                    "type": "string",
                    "description": "Main logo image URL",
                    "x-example": "/static/img/quay-horizontal-color.svg",
                },
                "footer_img": {
                    "type": "string",
                    "description": "Logo for UI footer",
                    "x-example": "/static/img/RedHat.svg",
                },
                "footer_url": {
                    "type": "string",
                    "description": "Link for footer image",
                    "x-example": "https://redhat.com",
                },
            },
        },
        "DOCUMENTATION_ROOT": {"type": "string", "description": "Root URL for documentation links"},
        # Health.
        "HEALTH_CHECKER": {
            "description": "The configured health check.",
            "x-example": ("RDSAwareHealthCheck", {"access_key": "foo", "secret_key": "bar"}),
        },
        # Metrics.
        "PROMETHEUS_NAMESPACE": {
            "type": "string",
            "description": "The prefix applied to all exposed Prometheus metrics. Defaults to `quay`",
            "x-example": "myregistry",
        },
        # Misc configuration.
        "BLACKLIST_V2_SPEC": {
            "type": "string",
            "description": "The Docker CLI versions to which Quay will respond that V2 is *unsupported*. Defaults to `<1.6.0`",
            "x-reference": "http://pythonhosted.org/semantic_version/reference.html#semantic_version.Spec",
            "x-example": "<1.8.0",
        },
        "USER_RECOVERY_TOKEN_LIFETIME": {
            "type": "string",
            "description": "The length of time a token for recovering a user accounts is valid. Defaults to 30m.",
            "x-example": "10m",
            "pattern": "^[0-9]+(w|m|d|h|s)$",
        },
        "SESSION_COOKIE_SECURE": {
            "type": "boolean",
            "description": "Whether the `secure` property should be set on session cookies. "
            + "Defaults to False. Recommended to be True for all installations using SSL.",
            "x-example": True,
            "x-reference": "https://en.wikipedia.org/wiki/Secure_cookies",
        },
        "PUBLIC_NAMESPACES": {
            "type": "array",
            "description": "If a namespace is defined in the public namespace list, then it will appear on *all*"
            + " user's repository list pages, regardless of whether that user is a member of the namespace."
            + ' Typically, this is used by an enterprise customer in configuring a set of "well-known"'
            + " namespaces.",
            "uniqueItems": True,
            "items": {
                "type": "string",
            },
        },
        "AVATAR_KIND": {
            "type": "string",
            "description": "The types of avatars to display, either generated inline (local) or Gravatar (gravatar)",
            "enum": ["local", "gravatar"],
        },
        "V2_PAGINATION_SIZE": {
            "type": "number",
            "description": "The number of results returned per page in V2 registry APIs",
            "x-example": 100,
        },
        "ENABLE_HEALTH_DEBUG_SECRET": {
            "type": ["string", "null"],
            "description": "If specified, a secret that can be given to health endpoints to see full debug info when"
            + "not authenticated as a superuser",
            "x-example": "somesecrethere",
        },
        "BROWSER_API_CALLS_XHR_ONLY": {
            "type": "boolean",
            "description": "If enabled, only API calls marked as being made by an XHR will be allowed from browsers. Defaults to True.",
            "x-example": False,
        },
        # Time machine and tag expiration settings.
        "FEATURE_CHANGE_TAG_EXPIRATION": {
            "type": "boolean",
            "description": "Whether users and organizations are allowed to change the tag expiration for tags in their namespace. Defaults to True.",
            "x-example": False,
        },
        "DEFAULT_TAG_EXPIRATION": {
            "type": "string",
            "description": "The default, configurable tag expiration time for time machine. Defaults to `2w`.",
            "pattern": "^[0-9]+(w|m|d|h|s)$",
        },
        "TAG_EXPIRATION_OPTIONS": {
            "type": "array",
            "description": "The options that users can select for expiration of tags in their namespace (if enabled)",
            "items": {
                "type": "string",
                "pattern": "^[0-9]+(w|m|d|h|s)$",
            },
        },
        # Team syncing.
        "FEATURE_TEAM_SYNCING": {
            "type": "boolean",
            "description": "Whether to allow for team membership to be synced from a backing group in the authentication engine (LDAP or Keystone)",
            "x-example": True,
        },
        "TEAM_RESYNC_STALE_TIME": {
            "type": "string",
            "description": "If team syncing is enabled for a team, how often to check its membership and resync if necessary (Default: 30m)",
            "x-example": "2h",
            "pattern": "^[0-9]+(w|m|d|h|s)$",
        },
        "FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP": {
            "type": "boolean",
            "description": "If enabled, non-superusers can setup syncing on teams to backing LDAP or Keystone. Defaults To False.",
            "x-example": True,
        },
        # Security scanning.
        "FEATURE_SECURITY_SCANNER": {
            "type": "boolean",
            "description": "Whether to turn of/off the security scanner. Defaults to False",
            "x-example": False,
            "x-reference": "https://coreos.com/quay-enterprise/docs/latest/security-scanning.html",
        },
        "FEATURE_SECURITY_NOTIFICATIONS": {
            "type": "boolean",
            "description": "If the security scanner is enabled, whether to turn of/off security notificaitons. Defaults to False",
            "x-example": False,
        },
        "SECURITY_SCANNER_V4_ENDPOINT": {
            "type": ["string", "null"],
            "pattern": "^http(s)?://(.)+$",
            "description": "The endpoint for the V4 security scanner",
            "x-example": "http://192.168.99.101:6060",
        },
        "SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE": {
            "type": ["string", "null"],
            "description": "Maxmum size for a layer to be indexed",
            "x-example": "8G",
        },
        "SECURITY_SCANNER_V4_MANIFEST_CLEANUP": {
            "type": "boolean",
            "description": "If the security scanner is enabled, whether or not to remove deleted manifests from the security scanner service. Defaults to False",
            "x-example": False,
        },
        "SECURITY_SCANNER_INDEXING_INTERVAL": {
            "type": "number",
            "description": "The number of seconds between indexing intervals in the security scanner. Defaults to 30.",
            "x-example": 30,
        },
        "SECURITY_SCANNER_V4_PSK": {
            "type": "string",
            "description": "A base64 encoded string used to sign JWT(s) on Clair V4 requests. If 'None' jwt signing will not occur.",
            "x-example": "PSK",
        },
        # Repository mirroring
        "REPO_MIRROR_INTERVAL": {
            "type": "number",
            "description": "The number of seconds between checking for repository mirror candidates. Defaults to 30.",
            "x-example": 30,
        },
        # Build
        "FEATURE_GITHUB_BUILD": {
            "type": "boolean",
            "description": "Whether to support GitHub build triggers. Defaults to False",
            "x-example": False,
        },
        "FEATURE_BITBUCKET_BUILD": {
            "type": "boolean",
            "description": "Whether to support Bitbucket build triggers. Defaults to False",
            "x-example": False,
        },
        "FEATURE_GITLAB_BUILD": {
            "type": "boolean",
            "description": "Whether to support GitLab build triggers. Defaults to False",
            "x-example": False,
        },
        "FEATURE_BUILD_SUPPORT": {
            "type": "boolean",
            "description": "Whether to support Dockerfile build. Defaults to True",
            "x-example": True,
        },
        "DEFAULT_NAMESPACE_MAXIMUM_BUILD_COUNT": {
            "type": ["number", "null"],
            "description": "If not None, the default maximum number of builds that can be queued in a namespace.",
            "x-example": 20,
        },
        "SUCCESSIVE_TRIGGER_INTERNAL_ERROR_DISABLE_THRESHOLD": {
            "type": ["number", "null"],
            "description": "If not None, the number of successive internal errors that can occur before a build trigger is automatically disabled. Defaults to 5.",
            "x-example": 10,
        },
        "SUCCESSIVE_TRIGGER_FAILURE_DISABLE_THRESHOLD": {
            "type": ["number", "null"],
            "description": "If not None, the number of successive failures that can occur before a build trigger is automatically disabled. Defaults to 100.",
            "x-example": 50,
        },
        # Nested repository names
        "FEATURE_EXTENDED_REPOSITORY_NAMES": {
            "type": "boolean",
            "description": "Whether repository names can have nested paths (/)",
            "x-example": True,
        },
        # Login
        "FEATURE_GITHUB_LOGIN": {
            "type": "boolean",
            "description": "Whether GitHub login is supported. Defaults to False",
            "x-example": False,
        },
        "FEATURE_GOOGLE_LOGIN": {
            "type": "boolean",
            "description": "Whether Google login is supported. Defaults to False",
            "x-example": False,
        },
        # Recaptcha
        "FEATURE_RECAPTCHA": {
            "type": "boolean",
            "description": "Whether Recaptcha is necessary for user login and recovery. Defaults to False",
            "x-example": False,
            "x-reference": "https://www.google.com/recaptcha/intro/",
        },
        "RECAPTCHA_SITE_KEY": {
            "type": ["string", "null"],
            "description": "If recaptcha is enabled, the site key for the Recaptcha service",
        },
        "RECAPTCHA_SECRET_KEY": {
            "type": ["string", "null"],
            "description": "If recaptcha is enabled, the secret key for the Recaptcha service",
        },
        # Pass through recaptcha for whitelisted users to support org/user creation via API
        "RECAPTCHA_WHITELISTED_USERS": {
            "type": "array",
            "description": "Quay usernames of those users allowed to create org/user via API bypassing recaptcha security check",
            "uniqueItems": True,
            "items": {
                "type": "string",
            },
        },
        # External application tokens.
        "FEATURE_APP_SPECIFIC_TOKENS": {
            "type": "boolean",
            "description": "If enabled, users can create tokens for use by the Docker CLI. Defaults to True",
            "x-example": False,
        },
        "APP_SPECIFIC_TOKEN_EXPIRATION": {
            "type": ["string", "null"],
            "description": "The expiration for external app tokens. Defaults to None.",
            "pattern": "^[0-9]+(w|m|d|h|s)$",
        },
        "EXPIRED_APP_SPECIFIC_TOKEN_GC": {
            "type": ["string", "null"],
            "description": "Duration of time expired external app tokens will remain before being garbage collected. Defaults to 1d.",
            "pattern": "^[0-9]+(w|m|d|h|s)$",
        },
        # Feature Flag: Garbage collection.
        "FEATURE_GARBAGE_COLLECTION": {
            "type": "boolean",
            "description": "Whether garbage collection of repositories is enabled. Defaults to True",
            "x-example": False,
        },
        # Feature Flag: Rate limits.
        "FEATURE_RATE_LIMITS": {
            "type": "boolean",
            "description": "Whether to enable rate limits on API and registry endpoints. Defaults to False",
            "x-example": True,
        },
        # Feature Flag: Aggregated log retrieval.
        "FEATURE_AGGREGATED_LOG_COUNT_RETRIEVAL": {
            "type": "boolean",
            "description": "Whether to allow retrieval of aggregated log counts. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Log export.
        "FEATURE_LOG_EXPORT": {
            "type": "boolean",
            "description": "Whether to allow exporting of action logs. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: User last accessed.
        "FEATURE_USER_LAST_ACCESSED": {
            "type": "boolean",
            "description": "Whether to record the last time a user was accessed. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Permanent Sessions.
        "FEATURE_PERMANENT_SESSIONS": {
            "type": "boolean",
            "description": "Whether sessions are permanent. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Super User Support.
        "FEATURE_SUPER_USERS": {
            "type": "boolean",
            "description": "Whether super users are supported. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Use FIPS compliant cryptography.
        "FEATURE_FIPS": {
            "type": "boolean",
            "description": "If set to true, Quay will run using FIPS compliant hash functions. Defaults to False",
            "x-example": True,
        },
        # Feature Flag: Anonymous Users.
        "FEATURE_ANONYMOUS_ACCESS": {
            "type": "boolean",
            "description": " Whether to allow anonymous users to browse and pull public repositories. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: User Creation.
        "FEATURE_USER_CREATION": {
            "type": "boolean",
            "description": "Whether users can be created (by non-super users). Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Invite Only User Creation.
        "FEATURE_INVITE_ONLY_USER_CREATION": {
            "type": "boolean",
            "description": "Whether users being created must be invited by another user. Defaults to False",
            "x-example": False,
        },
        # Feature Flag: Encrypted Basic Auth.
        "FEATURE_REQUIRE_ENCRYPTED_BASIC_AUTH": {
            "type": "boolean",
            "description": "Whether non-encrypted passwords (as opposed to encrypted tokens) can be used for basic auth. Defaults to False",
            "x-example": False,
        },
        # Feature Flag: Direct Login.
        "FEATURE_DIRECT_LOGIN": {
            "type": "boolean",
            "description": "Whether users can directly login to the UI. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Advertising V2.
        "FEATURE_ADVERTISE_V2": {
            "type": "boolean",
            "description": "Whether the v2/ endpoint is visible. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Log Rotation.
        "FEATURE_ACTION_LOG_ROTATION": {
            "type": "boolean",
            "description": "Whether or not to rotate old action logs to storage. Defaults to False",
            "x-example": False,
        },
        # Feature Flag: Library Support.
        "FEATURE_LIBRARY_SUPPORT": {
            "type": "boolean",
            "description": 'Whether to allow for "namespace-less" repositories when pulling and pushing from Docker. Defaults to True',
            "x-example": True,
        },
        # Feature Flag: Require Team Invite.
        "FEATURE_REQUIRE_TEAM_INVITE": {
            "type": "boolean",
            "description": "Whether to require invitations when adding a user to a team. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: Collecting and Supporting Metadata.
        "FEATURE_USER_METADATA": {
            "type": "boolean",
            "description": "Whether to collect and support user metadata. Defaults to False",
            "x-example": False,
        },
        # Feature Flag: Public Reposiotires in _catalog Endpoint.
        "FEATURE_PUBLIC_CATALOG": {
            "type": "boolean",
            "description": "If set to true, the _catalog endpoint returns public repositories. Otherwise, only private repositories can be returned. Defaults to False",
            "x-example": False,
        },
        # Feature Flag: Reader Build Logs.
        "FEATURE_READER_BUILD_LOGS": {
            "type": "boolean",
            "description": "If set to true, build logs may be read by those with read access to the repo, rather than only write access or admin access. Defaults to False",
            "x-example": False,
        },
        # Feature Flag: Usernames Autocomplete.
        "FEATURE_PARTIAL_USER_AUTOCOMPLETE": {
            "type": "boolean",
            "description": "If set to true, autocompletion will apply to partial usernames. Defaults to True",
            "x-example": True,
        },
        # Feature Flag: User log access.
        "FEATURE_USER_LOG_ACCESS": {
            "type": "boolean",
            "description": "If set to true, users will have access to audit logs for their namespace. Defaults to False",
            "x-example": True,
        },
        # Feature Flag: User renaming.
        "FEATURE_USER_RENAME": {
            "type": "boolean",
            "description": "If set to true, users can rename their own namespace. Defaults to False",
            "x-example": True,
        },
        # Feature Flag: Username confirmation.
        "FEATURE_USERNAME_CONFIRMATION": {
            "type": "boolean",
            "description": "If set to true, users can confirm their generated usernames. Defaults to True",
            "x-example": False,
        },
        # Feature Flag: V1 push restriction.
        "FEATURE_RESTRICTED_V1_PUSH": {
            "type": "boolean",
            "description": "If set to true, only namespaces listed in V1_PUSH_WHITELIST support V1 push. Defaults to True",
            "x-example": False,
        },
        # Feature Flag: Support Repository Mirroring.
        "FEATURE_REPO_MIRROR": {
            "type": "boolean",
            "description": "Whether to enable support for repository mirroring. Defaults to False",
            "x-example": False,
        },
        "REPO_MIRROR_TLS_VERIFY": {
            "type": "boolean",
            "description": "Require HTTPS and verify certificates of Quay registry during mirror. Defaults to True",
            "x-example": True,
        },
        "REPO_MIRROR_SERVER_HOSTNAME": {
            "type": ["string", "null"],
            "description": "Replaces the SERVER_HOSTNAME as the destination for mirroring. Defaults to unset",
            "x-example": "openshift-quay-service",
        },
        "REPO_MIRROR_ROLLBACK": {
            "type": ["boolean", "null"],
            "description": "Enables rolling repository back to previous state in the event the mirror fails. Defaults to false",
            "x-example": "true",
        },
        # Feature Flag: V1 push restriction.
        "V1_PUSH_WHITELIST": {
            "type": "array",
            "description": "The array of namespace names that support V1 push if FEATURE_RESTRICTED_V1_PUSH is set to true.",
            "x-example": ["some", "namespaces"],
        },
        # Logs model
        "LOGS_MODEL": {
            "type": "string",
            "description": "Logs model for action logs",
            "enum": ["database", "transition_reads_both_writes_es", "elasticsearch", "splunk"],
            "x-example": "database",
        },
        "LOGS_MODEL_CONFIG": {
            "type": "object",
            "description": "Logs model config for action logs",
            "properties": {
                "producer": {
                    "type": "string",
                    "description": "Logs producer",
                    "enum": ["kafka", "elasticsearch", "kinesis_stream", "splunk", "splunk_hec"],
                    "x-example": "kafka",
                },
                "elasticsearch_config": {
                    "type": "object",
                    "description": "Elasticsearch cluster configuration",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "Elasticsearch cluster endpoint",
                            "x-example": "host.elasticsearch.example",
                        },
                        "port": {
                            "type": "number",
                            "description": "Elasticsearch cluster endpoint port",
                            "x-example": 1234,
                        },
                        "access_key": {
                            "type": "string",
                            "description": "Elasticsearch user (or IAM key for AWS ES)",
                            "x-example": "some_string",
                        },
                        "secret_key": {
                            "type": "string",
                            "description": "Elasticsearch password (or IAM secret for AWS ES)",
                            "x-example": "some_secret_string",
                        },
                        "aws_region": {
                            "type": "string",
                            "description": "Amazon web service region",
                            "x-example": "us-east-1",
                        },
                        "use_ssl": {
                            "type": "boolean",
                            "description": "Use ssl for Elasticsearch. Defaults to True",
                            "x-example": True,
                        },
                        "index_prefix": {
                            "type": "string",
                            "description": "Elasticsearch's index prefix",
                            "x-example": "logentry_",
                        },
                        "index_settings": {
                            "type": "object",
                            "description": "Elasticsearch's index settings",
                        },
                    },
                },
                "kafka_config": {
                    "type": "object",
                    "description": "Kafka cluster configuration",
                    "properties": {
                        "bootstrap_servers": {
                            "type": "array",
                            "description": "List of Kafka brokers to bootstrap the client from",
                            "uniqueItems": True,
                            "items": {
                                "type": "string",
                            },
                        },
                        "topic": {
                            "type": "string",
                            "description": "Kafka topic to publish log entries to",
                            "x-example": "logentry",
                        },
                        "max_block_seconds": {
                            "type": "number",
                            "description": "Max number of seconds to block during a `send()`, either because the buffer is full or metadata unavailable",
                            "x-example": 10,
                        },
                    },
                },
                "kinesis_stream_config": {
                    "type": "object",
                    "description": "AWS Kinesis Stream configuration",
                    "properties": {
                        "stream_name": {
                            "type": "string",
                            "description": "Kinesis stream to send action logs to",
                            "x-example": "logentry-kinesis-stream",
                        },
                        "aws_region": {
                            "type": "string",
                            "description": "AWS region",
                            "x-example": "us-east-1",
                        },
                        "aws_access_key": {
                            "type": "string",
                            "description": "AWS access key",
                            "x-example": "some_access_key",
                        },
                        "aws_secret_key": {
                            "type": "string",
                            "description": "AWS secret key",
                            "x-example": "some_secret_key",
                        },
                        "connect_timeout": {
                            "type": "number",
                            "description": "Number of seconds before timeout when attempting to make a connection",
                            "x-example": 5,
                        },
                        "read_timeout": {
                            "type": "number",
                            "description": "Number of seconds before timeout when reading from a connection",
                            "x-example": 5,
                        },
                        "retries": {
                            "type": "number",
                            "description": "Max number of attempts made on a single request",
                            "x-example": 5,
                        },
                        "max_pool_connections": {
                            "type": "number",
                            "description": "The maximum number of connections to keep in a connection pool",
                            "x-example": 10,
                        },
                    },
                },
                "splunk_config": {
                    "type": "object",
                    "description": "Logs model config for splunk action logs/ splunk cluster configuration",
                    "x-reference": "https://dev.splunk.com/enterprise/docs/devtools/python/sdk-python"
                    "/howtousesplunkpython/howtogetdatapython#To-add-data-directly-to-an-index",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "Splunk cluster endpoint",
                            "x-example": "host.splunk.example",
                        },
                        "port": {
                            "type": "number",
                            "description": "Splunk management cluster endpoint port",
                            "x-example": 1234,
                        },
                        "bearer_token": {
                            "type": "string",
                            "description": "Bearer_Token for splunk.See: "
                            "https://dev.splunk.com/enterprise/docs/devtools/python/sdk-python"
                            "/howtousesplunkpython/howtoconnectpython/#Log-in-using-a-bearer-token",
                            "x-example": "us-east-1",
                        },
                        "url_scheme": {
                            "type": "string",
                            "description": "The url scheme for accessing the splunk service. If Splunk is behind SSL"
                            "*at all*, this *must* be `https`",
                            "enum": ["http", "https"],
                            "x-example": "https",
                        },
                        "verify_ssl": {
                            "type": "boolean",
                            "description": "Enable (True) or disable (False) SSL verification for https connections."
                            "Defaults to True",
                            "x-example": True,
                        },
                        "index_prefix": {
                            "type": "string",
                            "description": "Splunk's index prefix",
                            "x-example": "splunk_logentry_",
                        },
                        "ssl_ca_path": {
                            "type": "string",
                            "description": "*Relative container path* to a single .pem file containing a CA "
                            "certificate for SSL verification",
                            "x-example": "conf/stack/ssl-ca-cert.pem",
                        },
                    },
                },
                "splunk_hec_config": {
                    "type": "object",
                    "description": "Logs model config for splunk HTTP event collector action logs configuration",
                    "x-reference": "https://docs.splunk.com/Documentation/SplunkCloud/latest/Data/UsetheHTTPEventCollector#More_information_on_HEC_for_developers",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "Splunk cluster endpoint",
                            "x-example": "host.splunk.example",
                        },
                        "port": {
                            "type": "number",
                            "description": "Splunk management cluster endpoint port",
                            "x-example": 8080,
                            "default": 443,
                        },
                        "hec_token": {
                            "type": "string",
                            "description": "HEC token for splunk.",
                            "x-example": "1ad4d7bb-eed9-443a-897d-29e3b27df7a8",
                        },
                        "url_scheme": {
                            "type": "string",
                            "description": "The url scheme for accessing the splunk service. If Splunk is behind SSL"
                            "*at all*, this *must* be `https`",
                            "enum": ["http", "https"],
                            "x-example": "https",
                            "default": "https",
                        },
                        "verify_ssl": {
                            "type": "boolean",
                            "description": "Enable (True) or disable (False) SSL verification for https connections."
                            "Defaults to True",
                            "x-example": True,
                            "default": True,
                        },
                        "ssl_ca_path": {
                            "type": "string",
                            "description": "*Relative container path* to a single .pem file containing a CA "
                            "certificate for SSL verification",
                            "x-example": "conf/stack/ssl-ca-cert.pem",
                        },
                        "index": {
                            "type": "string",
                            "description": "The splunk index to use (overrides the token's default index).",
                            "x-example": "main",
                        },
                        "splunk_host": {
                            "type": "string",
                            "description": "The host name to log this event with (Defaults to the configured server hostname).",
                            "x-example": "quay.dev",
                            "default": "configured server hostname",
                        },
                        "splunk_sourcetype": {
                            "type": "string",
                            "description": "The name of the Splunk sourcetype to use.",
                            "x-example": "quay-sourcetype",
                            "default": "access_combined",
                        },
                    },
                    "required": ["host", "hec_token"],
                },
            },
        },
        # Feature Flag: Blacklist Email Domains
        "FEATURE_BLACKLISTED_EMAILS": {
            "type": "boolean",
            "description": "If set to true, no new User accounts may be created if their email domain is blacklisted.",
            "x-example": False,
        },
        # Blacklisted Email Domains
        "BLACKLISTED_EMAIL_DOMAINS": {
            "type": "array",
            "description": "The array of email-address domains that is used if FEATURE_BLACKLISTED_EMAILS is set to true.",
            "x-example": ["example.com", "example.org"],
        },
        "FRESH_LOGIN_TIMEOUT": {
            "type": "string",
            "description": "The time after which a fresh login requires users to reenter their password",
            "x-example": "5m",
        },
        # Webhook blacklist.
        "WEBHOOK_HOSTNAME_BLACKLIST": {
            "type": "array",
            "description": "The set of hostnames to disallow from webhooks when validating, beyond localhost",
            "x-example": ["somexternaldomain.com"],
        },
        "CREATE_PRIVATE_REPO_ON_PUSH": {
            "type": "boolean",
            "description": "Whether new repositories created by push are set to private visibility. Defaults to True.",
            "x-example": True,
        },
        "CREATE_NAMESPACE_ON_PUSH": {
            "type": "boolean",
            "description": "Whether new push to a non-existent organization creates it. Defaults to False.",
            "x-example": False,
        },
        # Allow first user to be initialized via API
        "FEATURE_USER_INITIALIZE": {
            "type": "boolean",
            "description": "If set to true, the first User account may be created via API /api/v1/user/initialize",
            "x-example": False,
        },
        # OCI artifact types
        "ALLOWED_OCI_ARTIFACT_TYPES": {
            "type": "object",
            "description": "The set of allowed OCI artifact mimetypes and the assiciated layer types",
            "x-example": {
                "application/vnd.cncf.helm.config.v1+json": ["application/tar+gzip"],
                "application/vnd.sylabs.sif.config.v1+json": [
                    "application/vnd.sylabs.sif.layer.v1.sif"
                ],
            },
        },
        "FEATURE_REFERRERS_API": {
            "type": "boolean",
            "description": "Enables OCI 1.1's referrers API",
            "x-example": False,
        },
        # Clean partial uploads during S3 multipart upload
        "CLEAN_BLOB_UPLOAD_FOLDER": {
            "type": "boolean",
            "description": "Automatically clean stale blobs leftover in the uploads storage folder from cancelled uploads",
            "x-example": False,
        },
        # Enable Quota Management
        "FEATURE_QUOTA_MANAGEMENT": {
            "type": "boolean",
            "description": "Enables configuration, caching, and validation for quota management feature",
            "x-example": False,
        },
        "FEATURE_QUOTA_SUPPRESS_FAILURES": {
            "type": "boolean",
            "description": "Catches and suppresses quota failures during image push and garbage collection",
            "x-example": False,
        },
        "DEFAULT_SYSTEM_REJECT_QUOTA_BYTES": {
            "type": "int",
            "description": "Enables system default quota reject byte allowance for all organizations",
            "x-example": False,
        },
        "QUOTA_TOTAL_DELAY_SECONDS": {
            "type": "int",
            "description": "The time to delay the Quota backfill operation. Must be set longer than the time required to complete the deployment.",
            "x-example": 30,
        },
        "QUOTA_BACKFILL": {
            "type": "boolean",
            "description": "Enables the quota backfill worker to calculate the size of pre-existing blobs",
            "x-example": True,
        },
        "QUOTA_BACKFILL_POLL_PERIOD": {
            "type": "int",
            "description": "The amount of time between runs of the quota backfill worker in seconds",
            "x-example": 15,
        },
        "QUOTA_BACKFILL_BATCH_SIZE": {
            "type": "int",
            "description": "The amount of namespaces that will be calculated for quota backfill on wakeup of the backfill worker.",
            "x-example": 100,
        },
        "QUOTA_INVALIDATE_TOTALS": {
            "type": "boolean",
            "description": "Invalidates totals when a write happens to a namespace and repository when FEATURE_QUOTA_MANAGEMENT is not enabled",
            "x-example": True,
        },
        "QUOTA_REGISTRY_SIZE_POLL_PERIOD": {
            "type": "int",
            "description": "The amount of time between runs of the quota registry size worker in seconds",
            "x-example": 30,
        },
        "FEATURE_EDIT_QUOTA": {
            "type": "boolean",
            "description": "Allow editing of quota configurations",
            "x-example": True,
        },
        "FEATURE_VERIFY_QUOTA": {
            "type": "boolean",
            "description": "Allow verification of quota on image push",
            "x-example": True,
        },
        "FEATURE_EXPORT_COMPLIANCE": {
            "type": "boolean",
            "description": "Use Red Hat Export Compliance Service during Red Hat SSO (only used in Quay.io)",
            "x-example": False,
        },
        "FEATURE_MANIFEST_SUBJECT_BACKFILL": {
            "type": "boolean",
            "description": "Enable the backfill worker to index existing manifest subjects",
            "x-example": True,
        },
        "UI_V2_FEEDBACK_FORM": {
            "type": "string",
            "description": "User feedback form for UI-V2",
            "x-example": "http://url-for-user-feedback-form.com",
        },
        "FEATURE_UI_V2": {
            "type": "boolean",
            "description": "Enables user to try the beta UI Environment",
            "x-example": False,
        },
        "EXPORT_COMPLIANCE_ENDPOINT": {
            "type": "string",
            "description": "The Red Hat Export Compliance Service Endpoint (only used in Quay.io)",
            "x-example": "export-compliance.com",
        },
        "CORS_ORIGIN": {
            "type": "array",
            "description": "Cross-Origin domain to allow requests from",
            "x-example": ["localhost:9000", "localhost:8080"],
        },
        "FEATURE_LISTEN_IP_VERSION": {
            "type": "string",
            "description": "Enables IPv4, IPv6 or dual-stack networking. Defaults to `IPv4`.",
            "x-example": "IPv4",
        },
        "GLOBAL_READONLY_SUPER_USERS": {
            "type": "array",
            "description": "Quay usernames of those super users to be granted global readonly privileges",
            "uniqueItems": True,
            "items": {
                "type": "string",
            },
        },
        "FEATURE_SUPERUSERS_FULL_ACCESS": {
            "type": "boolean",
            "description": "Grant superusers full access to repositories, registry-wide",
            "x-example": False,
        },
        "FEATURE_SUPERUSERS_ORG_CREATION_ONLY": {
            "type": "boolean",
            "description": "Whether to only allow superusers to create organizations",
            "x-example": False,
        },
        "FEATURE_RESTRICTED_USERS": {
            "type": "boolean",
            "description": "Grant non-whitelisted users restricted permissions",
            "x-example": False,
        },
        "RESTRICTED_USERS_WHITELIST": {
            "type": "array",
            "description": "Whitelisted users to exclude when FEATURE_RESTRICTED_USERS is enabled",
            "x-example": ["devtable"],
        },
        "FEATURE_SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX": {
            "type": "boolean",
            "description": "Whether to allow sending notifications about vulnerabilities for new pushes",
            "x-example": True,
        },
        "RESET_CHILD_MANIFEST_EXPIRATION": {
            "type": "boolean",
            "description": "When a manifest list is pushed, reset the expiry of the child manifest tags to become immediately eligible for GC on parent tag deletion",
            "x-example": True,
        },
        "PERMANENTLY_DELETE_TAGS": {
            "type": "boolean",
            "description": "Enables functionality related to the removal of tags from the time machine window",
            "x-example": True,
        },
        "FEATURE_ENTITLEMENT_RECONCILIATION": {
            "type": "boolean",
            "description": "Enable reconciler for internal RH marketplace",
            "x-example": False,
        },
        "ENTITLEMENT_RECONCILIATION_USER_ENDPOINT": {
            "type": "string",
            "description": "Endpoint for internal RH users API",
            "x-example": "https://internal-rh-user-endpoint",
        },
        "ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT": {
            "type": "string",
            "description": "Endpoint for internal RH marketplace API",
            "x-example": "https://internal-rh-marketplace-endpoint",
        },
        # Custom terms of service
        "TERMS_OF_SERVICE_URL": {
            "type": "string",
            "description": "Enable customizing of terms of service for on-prem installations",
            "x-example": "https://quay.io/tos",
        },
        "ROBOTS_DISALLOW": {
            "type": "boolean",
            "description": "If robot accounts are prevented from any interaction as well as from being created. Defaults to False",
        },
        "ROBOTS_WHITELIST": {
            "type": "array",
            "description": "List of robot accounts allowed for example, mirroring. Defaults to empty",
        },
        "FEATURE_AUTO_PRUNE": {
            "type": "boolean",
            "description": "Enable functionality related to the auto-pruning of tags",
            "x-example": False,
        },
        "FEATURE_UI_DELAY_AFTER_WRITE": {
            "type": "boolean",
            "description": "Adds a delay in the UI after each create operation. Useful if quay is reading from a different DB and there is replication delay between the write and read DBs. Defaults to False",
            "x-example": False,
        },
        "UI_DELAY_AFTER_WRITE_SECONDS": {
            "type": "int",
            "description": "Number of seconds to wait after a write operation in the UI",
            "x-example": 3,
        },
        "NOTIFICATION_MIN_SEVERITY_ON_NEW_INDEX": {
            "type": "string",
            "description": "Set minimal security level for new notifications on detected vulnerabilities. Avoids creation of large number of notifications after first index.",
            "x-example": "High",
        },
        "FEATURE_ASSIGN_OAUTH_TOKEN": {
            "type": "boolean",
            "description": "Allows organization administrators to assign OAuth tokens to other users",
            "x-example": False,
        },
        "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY": {
            "type": "object",
            "description": "Default auto-prune policy applied to all organizations and repositories",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "The method to prune tags by",
                    "enum": ["number_of_tags", "creation_date"],
                    "x-example": "number_of_tags",
                },
                "value": {
                    "type": ["string", "number"],
                    "description": "The value for the configured method. For number_of_tags it is a number denoting the number of tags to keep, for creation_date it is a string with the duration to keep tags for",
                    "x-example": "2d",
                },
            },
        },
        "FEATURE_IMAGE_EXPIRY_TRIGGER": {
            "type": "boolean",
            "description": "Allows users to set up notifications on image expiry",
            "x-example": False,
        },
        "NOTIFICATION_TASK_RUN_MINIMUM_INTERVAL_MINUTES": {
            "type": "number",
            "description": "Interval in minutes that defines frequency to re-run notifications",
            "x-example": 5000,
        },
        "DISABLE_PUSHES": {
            "type": "boolean",
            "description": "Only disables pushes of new content to the registry, while retaining all other functionality. Differs from read only mode because database is not set as read-only.",
            "x-example": False,
        },
        "MANIFESTS_ENDPOINT_READ_TIMEOUT": {
            "type": "string",
            "description": "Nginx read timeout for manifests endpoints used by pulls and pushes",
            "x-example": "5m",
        },
    },
}
