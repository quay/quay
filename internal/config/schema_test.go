package config

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// knownUnmapped lists Python schema properties intentionally not yet mapped to
// Go struct fields. This list should shrink over time as coverage increases.
var knownUnmapped = map[string]bool{
	// SSL/TLS
	"SSL_CIPHERS":   true,
	"SSL_PROTOCOLS": true,

	// User-visible
	"CONTACT_INFO":                 true,
	"SEARCH_RESULTS_PER_PAGE":      true,
	"SEARCH_MAX_RESULT_PAGE_COUNT": true,

	// Email
	"MAIL_SERVER":         true,
	"MAIL_USE_TLS":        true,
	"MAIL_PORT":           true,
	"MAIL_USERNAME":       true,
	"MAIL_PASSWORD":       true,
	"MAIL_DEFAULT_SENDER": true,

	// Database extras
	"DB_CONNECTION_POOLING":              true,
	"ALLOW_PULLS_WITHOUT_STRICT_LOGGING": true,
	"ALLOW_WITHOUT_STRICT_LOGGING":       true,

	// Storage extras
	"FEATURE_PROXY_CACHE":               true,
	"FEATURE_PROXY_CACHE_BLOB_DOWNLOAD": true,
	"MAXIMUM_LAYER_SIZE":                true,
	"USERFILES_LOCATION":                true,
	"USERFILES_PATH":                    true,

	// Audit/Logging
	"ACTION_LOG_AUDIT_LOGINS":          true,
	"ACTION_LOG_AUDIT_LOGIN_FAILURES":  true,
	"ACTION_LOG_AUDIT_PULL_FAILURES":   true,
	"ACTION_LOG_AUDIT_PUSH_FAILURES":   true,
	"ACTION_LOG_AUDIT_DELETE_FAILURES": true,
	"ACTION_LOG_ARCHIVE_LOCATION":      true,
	"ACTION_LOG_ARCHIVE_PATH":          true,
	"ACTION_LOG_ROTATION_THRESHOLD":    true,
	"LOG_ARCHIVE_LOCATION":             true,
	"LOG_ARCHIVE_PATH":                 true,

	// OAuth
	"DIRECT_OAUTH_CLIENTID_WHITELIST": true,
	"GITHUB_LOGIN_CONFIG":             true,
	"BITBUCKET_TRIGGER_CONFIG":        true,
	"GITHUB_TRIGGER_CONFIG":           true,
	"GOOGLE_LOGIN_CONFIG":             true,
	"GITLAB_TRIGGER_CONFIG":           true,

	// Branding
	"BRANDING":           true,
	"DOCUMENTATION_ROOT": true,

	// Health/Metrics
	"HEALTH_CHECKER":       true,
	"PROMETHEUS_NAMESPACE": true,
	"TRACKED_NAMESPACES":   true,

	// Misc
	"BLACKLIST_V2_SPEC":            true,
	"USER_RECOVERY_TOKEN_LIFETIME": true,
	"SESSION_COOKIE_SECURE":        true,
	"PUBLIC_NAMESPACES":            true,
	"AVATAR_KIND":                  true,
	"V2_PAGINATION_SIZE":           true,
	"ENABLE_HEALTH_DEBUG_SECRET":   true,
	"BROWSER_API_CALLS_XHR_ONLY":   true,

	// Time machine
	"FEATURE_IMMUTABLE_TAGS":            true,
	"FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE": true,

	// Team syncing
	"FEATURE_TEAM_SYNCING":                    true,
	"TEAM_RESYNC_STALE_TIME":                  true,
	"FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP": true,

	// Security scanner extras
	"FEATURE_SECURITY_NOTIFICATIONS":          true,
	"SECURITY_SCANNER_V4_NAMESPACE_WHITELIST": true,
	"SECURITY_SCANNER_V4_PSK":                 true,
	"SECURITY_SCANNER_V4_MANIFEST_CLEANUP":    true,

	// Feature flags not yet mapped
	"FEATURE_ADVERTISE_V2":                          true,
	"FEATURE_EXTENDED_ACTION_LOGGING":               true,
	"FEATURE_AGGREGATED_LOG_COUNT_RETRIEVAL":        true,
	"FEATURE_ACTION_LOG_ROTATION":                   true,
	"FEATURE_ASSIGN_OAUTH_TOKEN":                    true,
	"FEATURE_AUTO_PRUNE":                            true,
	"FEATURE_BITBUCKET_BUILD":                       true,
	"FEATURE_BLACKLISTED_EMAILS":                    true,
	"FEATURE_DISABLE_OIDC_FALLBACK_GROUPS_CREATION": true,
	"FEATURE_EDIT_QUOTA":                            true,
	"FEATURE_ENTITLEMENT_RECONCILIATION":            true,
	"FEATURE_EXPORT_COMPLIANCE":                     true,
	"FEATURE_EXTENDED_REPOSITORY_NAMES":             true,
	"FEATURE_FIPS":                                  true,
	"FEATURE_GARBAGE_COLLECTION":                    true,
	"FEATURE_GITHUB_BUILD":                          true,
	"FEATURE_GITHUB_LOGIN":                          true,
	"FEATURE_GITLAB_BUILD":                          true,
	"FEATURE_GLOBAL_READONLY_SUPER_USERS":           true,
	"FEATURE_GOOGLE_LOGIN":                          true,
	"FEATURE_IMAGE_EXPIRY_TRIGGER":                  true,
	"FEATURE_INVITE_ONLY_USER_CREATION":             true,
	"FEATURE_LIBRARY_SUPPORT":                       true,
	"FEATURE_LISTEN_IP_VERSION":                     true,
	"FEATURE_LOG_EXPORT":                            true,
	"FEATURE_MANIFEST_SUBJECT_BACKFILL":             true,
	"FEATURE_ORG_MIRROR":                            true,
	"FEATURE_OTEL_TRACING":                          true,
	"FEATURE_PARTIAL_USER_AUTOCOMPLETE":             true,
	"FEATURE_PERMANENT_SESSIONS":                    true,
	"FEATURE_PUBLIC_CATALOG":                        true,
	"FEATURE_QUOTA_MANAGEMENT":                      true,
	"FEATURE_QUOTA_SUPPRESS_FAILURES":               true,
	"FEATURE_RATE_LIMITS":                           true,
	"FEATURE_READER_BUILD_LOGS":                     true,
	"FEATURE_READONLY_APP_REGISTRY":                 true,
	"FEATURE_RECAPTCHA":                             true,
	"FEATURE_REFERRERS_API":                         true,
	"FEATURE_REQUIRE_ENCRYPTED_BASIC_AUTH":          true,
	"FEATURE_REQUIRE_TEAM_INVITE":                   true,
	"FEATURE_RESTRICTED_USERS":                      true,
	"FEATURE_RESTRICTED_V1_PUSH":                    true,
	"FEATURE_SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX":  true,
	"FEATURE_SPARSE_INDEX":                          true,
	"FEATURE_SUPERUSERS_FULL_ACCESS":                true,
	"FEATURE_SUPERUSERS_ORG_CREATION_ONLY":          true,
	"FEATURE_SUPERUSER_CONFIGDUMP":                  true,
	"FEATURE_SUPER_USERS":                           true,
	"FEATURE_UI":                                    true,
	"FEATURE_UI_DELAY_AFTER_WRITE":                  true,
	"FEATURE_UI_MODELCARD":                          true,
	"FEATURE_UI_V2":                                 true,
	"FEATURE_USER_EVENTS":                           true,
	"FEATURE_USER_INITIALIZE":                       true,
	"FEATURE_USER_LAST_ACCESSED":                    true,
	"FEATURE_USER_LOG_ACCESS":                       true,
	"FEATURE_USER_METADATA":                         true,
	"FEATURE_USER_RENAME":                           true,
	"FEATURE_USERNAME_CONFIRMATION":                 true,
	"FEATURE_VERIFY_QUOTA":                          true,

	// Triggers & entitlements
	"SUCCESSIVE_TRIGGER_FAILURE_DISABLE_THRESHOLD":        true,
	"SUCCESSIVE_TRIGGER_INTERNAL_ERROR_DISABLE_THRESHOLD": true,
	"ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT":     true,
	"ENTITLEMENT_RECONCILIATION_PASSWORD":                 true,
	"ENTITLEMENT_RECONCILIATION_USER":                     true,
	"ENTITLEMENT_RECONCILIATION_USER_ENDPOINT":            true,

	// Repo mirror
	"REPO_MIRROR_INTERVAL":        true,
	"REPO_MIRROR_ROLLBACK":        true,
	"REPO_MIRROR_SERVER_HOSTNAME": true,
	"REPO_MIRROR_TLS_VERIFY":      true,

	// Quotas
	"DEFAULT_SYSTEM_REJECT_QUOTA_BYTES": true,
	"QUOTA_BACKFILL":                    true,
	"QUOTA_BACKFILL_BATCH_SIZE":         true,
	"QUOTA_BACKFILL_POLL_PERIOD":        true,
	"QUOTA_INVALIDATE_TOTALS":           true,
	"QUOTA_REGISTRY_SIZE_POLL_PERIOD":   true,
	"QUOTA_TOTAL_DELAY_SECONDS":         true,

	// UI
	"DISABLE_ANGULAR_UI":            true,
	"UI_DELAY_AFTER_WRITE_SECONDS":  true,
	"UI_MODELCARD_ANNOTATION":       true,
	"UI_MODELCARD_ARTIFACT_TYPE":    true,
	"UI_MODELCARD_LAYER_ANNOTATION": true,
	"UI_V2_FEEDBACK_FORM":           true,
	"FOOTER_LINKS":                  true,

	// Observability
	"LOGS_MODEL":                 true,
	"LOGS_MODEL_CONFIG":          true,
	"OTEL_CONFIG":                true,
	"OTEL_TRACING_EXCLUDED_URLS": true,

	// Security / access
	"SSRF_ALLOWED_HOSTS":          true,
	"CORS_ORIGIN":                 true,
	"EXPORT_COMPLIANCE_ENDPOINT":  true,
	"RECAPTCHA_SECRET_KEY":        true,
	"RECAPTCHA_SITE_KEY":          true,
	"RECAPTCHA_WHITELISTED_USERS": true,
	"V1_PUSH_WHITELIST":           true,
	"WEBHOOK_HOSTNAME_BLACKLIST":  true,
	"RESTRICTED_USERS_WHITELIST":  true,
	"BLACKLISTED_EMAIL_DOMAINS":   true,
	"ROBOTS_WHITELIST":            true,

	// Misc continued
	"ALLOWED_OCI_ARTIFACT_TYPES":                     true,
	"APP_SPECIFIC_TOKEN_EXPIRATION":                  true,
	"AUTO_PRUNE_DEFAULT_POLICY":                      true,
	"CLEAN_BLOB_UPLOAD_FOLDER":                       true,
	"CREATE_NAMESPACE_ON_PUSH":                       true,
	"CREATE_PRIVATE_REPO_ON_PUSH":                    true,
	"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY":             true,
	"DEFAULT_NAMESPACE_MAXIMUM_BUILD_COUNT":          true,
	"DISABLE_PUSHES":                                 true,
	"ENTERPRISE_LOGO_URL":                            true,
	"EXPIRED_APP_SPECIFIC_TOKEN_GC":                  true,
	"FRESH_LOGIN_TIMEOUT":                            true,
	"GLOBAL_READONLY_SUPER_USERS":                    true,
	"IGNORE_UNKNOWN_MEDIATYPES":                      true,
	"MANIFESTS_ENDPOINT_READ_TIMEOUT":                true,
	"NON_RATE_LIMITED_NAMESPACES":                    true,
	"NOTIFICATION_MIN_SEVERITY_ON_NEW_INDEX":         true,
	"NOTIFICATION_TASK_RUN_MINIMUM_INTERVAL_MINUTES": true,
	"ORG_MIRROR_INTERVAL":                            true,
	"PERMANENTLY_DELETE_TAGS":                        true,
	"RESET_CHILD_MANIFEST_EXPIRATION":                true,
	"ROBOTS_DISALLOW":                                true,
	"SECURITY_SCANNER_INDEXING_INTERVAL":             true,
	"SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE":       true,
	"SPARSE_INDEX_REQUIRED_ARCHS":                    true,
	"WEBHOOK_NOTIFICATION_CONFIG":                    true,
}

// goOnlyFields lists Go struct fields that intentionally have no corresponding
// Python CONFIG_SCHEMA property. These are internal fields (e.g., from
// INTERNAL_ONLY_PROPERTIES) that the Go CLI needs but are not part of the
// public schema.
var goOnlyFields = map[string]bool{
	"DATABASE_SECRET_KEY": true,
	"SECRET_KEY":          true,
}

// TestSchemaFieldCoverage compares the Python schema keys against the Go struct
// tags. It catches drift in both directions.
func TestSchemaFieldCoverage(t *testing.T) {
	// Find schema.py relative to this test file.
	schemaPath := filepath.Join("..", "..", "util", "config", "schema.py")
	if _, err := os.Stat(schemaPath); os.IsNotExist(err) {
		t.Skip("util/config/schema.py not found; skipping drift test")
	}

	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("python3 not available; skipping drift test")
	}

	script := `
import json, sys
sys.path.insert(0, ".")
g = {}
exec(open("` + schemaPath + `").read(), g)
print(json.dumps(sorted(g["CONFIG_SCHEMA"]["properties"].keys())))
`
	out, err := exec.CommandContext(t.Context(), python, "-c", script).CombinedOutput()
	require.NoError(t, err, "python3 failed: %s", out)

	var pythonKeys []string
	require.NoError(t, json.Unmarshal(out, &pythonKeys), "json.Unmarshal python output")

	goTags := knownYAMLTags(Config{})

	// Check: Python keys missing from Go (not in knownUnmapped).
	var missingInGo []string
	for _, k := range pythonKeys {
		if !goTags[k] && !knownUnmapped[k] {
			missingInGo = append(missingInGo, k)
		}
	}
	sort.Strings(missingInGo)
	assert.Empty(t, missingInGo,
		"Python schema keys missing from Go struct and not in knownUnmapped.\n"+
			"Add these fields to the Config struct or to knownUnmapped")

	// Check: Go tags not in Python schema.
	pythonSet := make(map[string]bool, len(pythonKeys))
	for _, k := range pythonKeys {
		pythonSet[k] = true
	}

	var extraInGo []string
	for tag := range goTags {
		if !pythonSet[tag] && !knownUnmapped[tag] && !goOnlyFields[tag] {
			extraInGo = append(extraInGo, tag)
		}
	}
	sort.Strings(extraInGo)
	assert.Empty(t, extraInGo,
		"Go struct tags not in Python schema.\n"+
			"These fields may have been removed from the Python schema")

	// Check: knownUnmapped entries that are now mapped in Go.
	var staleUnmapped []string
	for k := range knownUnmapped {
		if goTags[k] {
			staleUnmapped = append(staleUnmapped, k)
		}
	}
	sort.Strings(staleUnmapped)
	assert.Empty(t, staleUnmapped,
		"knownUnmapped entries that now have Go struct fields (remove from knownUnmapped)")
}
