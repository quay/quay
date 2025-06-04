import os
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from config import DefaultConfig


class FakeTransaction(object):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        pass


TEST_DB_FILE = NamedTemporaryFile(delete=True)


class TestConfig(DefaultConfig):
    TESTING = True
    SECRET_KEY = "superdupersecret!!!1"
    DATABASE_SECRET_KEY = "anothercrazykey!"
    BILLING_TYPE = "FakeStripe"

    TEST_DB_FILE = TEST_DB_FILE
    DB_URI = os.environ.get("TEST_DATABASE_URI", "sqlite:///{0}".format(TEST_DB_FILE.name))
    DB_CONNECTION_ARGS = {
        "threadlocals": True,
        "autorollback": True,
    }

    @staticmethod
    def create_transaction(db):
        return FakeTransaction()

    DB_TRANSACTION_FACTORY = create_transaction

    DISTRIBUTED_STORAGE_CONFIG = {"local_us": ["FakeStorage", {}], "local_eu": ["FakeStorage", {}]}
    DISTRIBUTED_STORAGE_PREFERENCE = ["local_us"]

    BUILDLOGS_MODULE_AND_CLASS = ("test.testlogs", "testlogs.TestBuildLogs")
    BUILDLOGS_OPTIONS = ["devtable", "building", "deadbeef-dead-beef-dead-beefdeadbeef", False]

    USERFILES_LOCATION = "local_us"
    USERFILES_PATH = "userfiles/"

    FEATURE_SUPER_USERS = True
    FEATURE_BILLING = True
    FEATURE_MAILING = True
    SUPER_USERS = ["devtable"]
    GLOBAL_READONLY_SUPER_USERS = ["globalreadonlysuperuser"]

    LICENSE_USER_LIMIT = 500
    LICENSE_EXPIRATION = datetime.now() + timedelta(weeks=520)
    LICENSE_EXPIRATION_WARNING = datetime.now() + timedelta(weeks=520)

    FEATURE_GITHUB_BUILD = True

    CLOUDWATCH_NAMESPACE = None

    FEATURE_SECURITY_SCANNER = True
    FEATURE_SECURITY_NOTIFICATIONS = True
    SECURITY_SCANNER_V4_ENDPOINT = "http://fakesecurityscanner/"

    FEATURE_SIGNING = True

    INSTANCE_SERVICE_KEY_KID_LOCATION = "test/data/test.kid"
    INSTANCE_SERVICE_KEY_LOCATION = "test/data/test.pem"

    PROMETHEUS_PUSHGATEWAY_URL = None

    GITHUB_LOGIN_CONFIG: Optional[Dict[str, Any]] = {}
    GOOGLE_LOGIN_CONFIG: Optional[Dict[str, Any]] = {}

    FEATURE_GITHUB_LOGIN = True
    FEATURE_GOOGLE_LOGIN = True

    TESTOIDC_LOGIN_CONFIG = {
        "CLIENT_ID": "foo",
        "CLIENT_SECRET": "bar",
        "OIDC_SERVER": "http://fakeoidc",
        "DEBUGGING": True,
        "LOGIN_BINDING_FIELD": "sub",
    }

    RECAPTCHA_SITE_KEY = "somekey"
    RECAPTCHA_SECRET_KEY = "somesecretkey"
    RECAPTCHA_WHITELISTED_USERS: List[str] = []

    FEATURE_TEAM_SYNCING = True
    FEATURE_CHANGE_TAG_EXPIRATION = True

    TAG_EXPIRATION_OPTIONS = ["0s", "1s", "1d", "1w", "2w", "4w"]

    DEFAULT_NAMESPACE_MAXIMUM_BUILD_COUNT = None

    DATA_MODEL_CACHE_CONFIG = {
        "engine": "inmemory",
        # OCI Conformance tests don't expect results to be cached.
        # If we implement cache invalidation, we can enable it back.
        "active_repo_tags_cache_ttl": "0s",
    }

    FEATURE_REPO_MIRROR = True
    FEATURE_GENERAL_OCI_SUPPORT = True
    OCI_NAMESPACE_WHITELIST: List[str] = []

    FEATURE_USER_INITIALIZE = True

    FEATURE_QUOTA_MANAGEMENT = True
    FEATURE_EDIT_QUOTA = True
    FEATURE_VERIFY_QUOTA = True
    FEATURE_QUOTA_SUPPRESS_FAILURES = False
    DEFAULT_SYSTEM_REJECT_QUOTA_BYTES = 0
    FEATURE_PROXY_CACHE = True
    PERMANENTLY_DELETE_TAGS = True
    RESET_CHILD_MANIFEST_EXPIRATION = True

    FEATURE_RH_MARKETPLACE = True

    FEATURE_AUTO_PRUNE = True
    ACTION_LOG_AUDIT_LOGINS = True
    ACTION_LOG_AUDIT_LOGIN_FAILURES = True
    ACTION_LOG_AUDIT_PULL_FAILURES = True
    ACTION_LOG_AUDIT_PUSH_FAILURES = True
    ACTION_LOG_AUDIT_DELETE_FAILURES = True
    AUTOPRUNE_FETCH_TAGS_PAGE_LIMIT = 2
    AUTOPRUNE_FETCH_REPOSITORIES_PAGE_LIMIT = 2
    FEATURE_IMAGE_EXPIRY_TRIGGER = True

    CDN_SPECIFIC_NAMESPACES = ["redhat"]
