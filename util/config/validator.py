import logging

from auth.auth_context import get_authenticated_user
from data.users import LDAP_CERT_FILENAME
from util.secscan.secscan_util import get_blob_download_uri_getter
from util.config import URLSchemeAndHostname

from util.config.validators.validate_database import DatabaseValidator
from util.config.validators.validate_redis import RedisValidator
from util.config.validators.validate_storage import StorageValidator
from util.config.validators.validate_ldap import LDAPValidator
from util.config.validators.validate_keystone import KeystoneValidator
from util.config.validators.validate_jwt import JWTAuthValidator
from util.config.validators.validate_secscan import SecurityScannerValidator
from util.config.validators.validate_ssl import SSLValidator, SSL_FILENAMES
from util.config.validators.validate_google_login import GoogleLoginValidator
from util.config.validators.validate_bitbucket_trigger import BitbucketTriggerValidator
from util.config.validators.validate_gitlab_trigger import GitLabTriggerValidator
from util.config.validators.validate_github import GitHubLoginValidator, GitHubTriggerValidator
from util.config.validators.validate_oidc import OIDCLoginValidator
from util.config.validators.validate_timemachine import TimeMachineValidator
from util.config.validators.validate_access import AccessSettingsValidator
from util.config.validators.validate_actionlog_archiving import ActionLogArchivingValidator
from util.config.validators.validate_apptokenauth import AppTokenAuthValidator
from util.config.validators.validate_elasticsearch import ElasticsearchValidator
from util.config.validators.validate_kinesis import KinesisValidator

logger = logging.getLogger(__name__)


class ConfigValidationException(Exception):
    """
    Exception raised when the configuration fails to validate for a known reason.
    """

    pass


# Note: Only add files required for HTTPS to the SSL_FILESNAMES list.
DB_SSL_FILENAMES = ["database.pem"]
JWT_FILENAMES = ["jwt-authn.cert"]
ACI_CERT_FILENAMES = ["signing-public.gpg", "signing-private.gpg"]
LDAP_FILENAMES = [LDAP_CERT_FILENAME]
CONFIG_FILENAMES = (
    SSL_FILENAMES + DB_SSL_FILENAMES + JWT_FILENAMES + ACI_CERT_FILENAMES + LDAP_FILENAMES
)
CONFIG_FILE_SUFFIXES = ["-cloudfront-signing-key.pem"]
EXTRA_CA_DIRECTORY = "extra_ca_certs"
EXTRA_CA_DIRECTORY_PREFIX = "extra_ca_certs_"

VALIDATORS = {
    DatabaseValidator.name: DatabaseValidator.validate,
    RedisValidator.name: RedisValidator.validate,
    StorageValidator.name: StorageValidator.validate,
    GitHubLoginValidator.name: GitHubLoginValidator.validate,
    GitHubTriggerValidator.name: GitHubTriggerValidator.validate,
    GitLabTriggerValidator.name: GitLabTriggerValidator.validate,
    BitbucketTriggerValidator.name: BitbucketTriggerValidator.validate,
    GoogleLoginValidator.name: GoogleLoginValidator.validate,
    SSLValidator.name: SSLValidator.validate,
    LDAPValidator.name: LDAPValidator.validate,
    JWTAuthValidator.name: JWTAuthValidator.validate,
    KeystoneValidator.name: KeystoneValidator.validate,
    SecurityScannerValidator.name: SecurityScannerValidator.validate,
    OIDCLoginValidator.name: OIDCLoginValidator.validate,
    TimeMachineValidator.name: TimeMachineValidator.validate,
    AccessSettingsValidator.name: AccessSettingsValidator.validate,
    ActionLogArchivingValidator.name: ActionLogArchivingValidator.validate,
    AppTokenAuthValidator.name: AppTokenAuthValidator.validate,
    ElasticsearchValidator.name: ElasticsearchValidator.validate,
    KinesisValidator.name: KinesisValidator.validate,
}


def validate_service_for_config(service, validator_context):
    """
    Attempts to validate the configuration for the given service.
    """
    if not service in VALIDATORS:
        return {"status": False}

    try:
        VALIDATORS[service](validator_context)
        return {"status": True}
    except Exception as ex:
        logger.exception("Validation exception")
        return {"status": False, "reason": str(ex)}


def is_valid_config_upload_filename(filename):
    """
    Returns true if and only if the given filename is one which is supported for upload from the
    configuration UI tool.
    """
    if filename in CONFIG_FILENAMES:
        return True

    return any([filename.endswith(suffix) for suffix in CONFIG_FILE_SUFFIXES])


class ValidatorContext(object):
    """
    Context to run validators in, with any additional runtime configuration they need.
    """

    def __init__(
        self,
        config,
        user_password=None,
        http_client=None,
        context=None,
        url_scheme_and_hostname=None,
        jwt_auth_max=None,
        registry_title=None,
        ip_resolver=None,
        feature_sec_scanner=False,
        is_testing=False,
        uri_creator=None,
        config_provider=None,
        instance_keys=None,
        init_scripts_location=None,
    ):
        self.config = config
        self.user = get_authenticated_user()
        self.user_password = user_password
        self.http_client = http_client
        self.context = context
        self.url_scheme_and_hostname = url_scheme_and_hostname
        self.jwt_auth_max = jwt_auth_max
        self.registry_title = registry_title
        self.ip_resolver = ip_resolver
        self.feature_sec_scanner = feature_sec_scanner
        self.is_testing = is_testing
        self.uri_creator = uri_creator
        self.config_provider = config_provider
        self.instance_keys = instance_keys
        self.init_scripts_location = init_scripts_location

    @classmethod
    def from_app(
        cls,
        app,
        config,
        user_password,
        ip_resolver,
        instance_keys,
        client=None,
        config_provider=None,
        init_scripts_location=None,
    ):
        """
        Creates a ValidatorContext from an app config, with a given config to validate.

        :param app: the Flask app to pull configuration information from
        :param config: the config to validate
        :param user_password: request password
        :param instance_keys: The instance keys handler
        :param ip_resolver: an App
        :param client: http client used to connect to services
        :param config_provider: config provider used to access config volume(s)
        :param init_scripts_location: location where initial load scripts are stored
        :return: ValidatorContext
        """
        url_scheme_and_hostname = URLSchemeAndHostname.from_app_config(app.config)

        return cls(
            config,
            user_password=user_password,
            http_client=client or app.config["HTTPCLIENT"],
            context=app.app_context,
            url_scheme_and_hostname=url_scheme_and_hostname,
            jwt_auth_max=app.config.get("JWT_AUTH_MAX_FRESH_S", 300),
            registry_title=app.config["REGISTRY_TITLE"],
            ip_resolver=ip_resolver,
            feature_sec_scanner=app.config.get("FEATURE_SECURITY_SCANNER", False),
            is_testing=app.config.get("TESTING", False),
            uri_creator=get_blob_download_uri_getter(
                app.test_request_context("/"), url_scheme_and_hostname
            ),
            config_provider=config_provider,
            instance_keys=instance_keys,
            init_scripts_location=init_scripts_location,
        )
