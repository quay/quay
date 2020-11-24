import hashlib
import json
import logging
import os

from functools import partial

from Crypto.PublicKey import RSA
from flask import Flask, request, Request
from flask_login import LoginManager
from flask_mail import Mail
from flask_principal import Principal
from jwkest.jwk import RSAKey
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.exceptions import HTTPException

import features

from _init import (
    config_provider,
    CONF_DIR,
    IS_KUBERNETES,
    IS_TESTING,
    OVERRIDE_CONFIG_DIRECTORY,
    IS_BUILDING,
)

from avatars.avatars import Avatar
from buildman.manager.buildcanceller import BuildCanceller
from data import database
from data import model
from data import logs_model
from data.archivedlogs import LogArchive
from data.billing import Billing
from data.buildlogs import BuildLogs
from data.cache import get_model_cache
from data.model.user import LoginWrappedDBUser
from data.queue import WorkQueue
from data.userevent import UserEventsBuilderModule
from data.userfiles import Userfiles
from data.users import UserAuthentication
from data.registry_model import registry_model
from data.secscan_model import secscan_model
from image.oci import register_artifact_type
from path_converters import (
    RegexConverter,
    RepositoryPathConverter,
    APIRepositoryPathConverter,
)
from oauth.services.github import GithubOAuthService
from oauth.services.gitlab import GitLabOAuthService
from oauth.loginmanager import OAuthLoginManager
from storage import Storage
from util.log import filter_logs
from util import get_app_url
from util.secscan.secscan_util import get_blob_download_uri_getter
from util.ipresolver import IPResolver
from util.saas.analytics import Analytics
from util.saas.exceptionlog import Sentry
from util.names import urn_generator
from util.config import URLSchemeAndHostname
from util.config.configutil import generate_secret_key
from util.config.superusermanager import SuperUserManager
from util.label_validator import LabelValidator
from util.metrics.prometheus import PrometheusPlugin
from util.repomirror.api import RepoMirrorAPI
from util.tufmetadata.api import TUFMetadataAPI
from util.security.instancekeys import InstanceKeys
from util.greenlet_tracing import enable_tracing


OVERRIDE_CONFIG_YAML_FILENAME = os.path.join(OVERRIDE_CONFIG_DIRECTORY, "config.yaml")
OVERRIDE_CONFIG_PY_FILENAME = os.path.join(OVERRIDE_CONFIG_DIRECTORY, "config.py")

OVERRIDE_CONFIG_KEY = "QUAY_OVERRIDE_CONFIG"

DOCKER_V2_SIGNINGKEY_FILENAME = "docker_v2.pem"
INIT_SCRIPTS_LOCATION = "/conf/init/"

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Instantiate the configuration.
is_testing = IS_TESTING
is_kubernetes = IS_KUBERNETES
is_building = IS_BUILDING

if is_testing:
    from test.testconfig import TestConfig

    logger.debug("Loading test config.")
    app.config.from_object(TestConfig())
else:
    from config import DefaultConfig

    logger.debug("Loading default config.")
    app.config.from_object(DefaultConfig())
    app.teardown_request(database.close_db_filter)

# Load the override config via the provider.
config_provider.update_app_config(app.config)

# Update any configuration found in the override environment variable.
environ_config = json.loads(os.environ.get(OVERRIDE_CONFIG_KEY, "{}"))
app.config.update(environ_config)

# Fix remote address handling for Flask.
if app.config.get("PROXY_COUNT", 1):
    app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=app.config.get("PROXY_COUNT", 1))

# Allow user to define a custom storage preference for the local instance.
_distributed_storage_preference = os.environ.get("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", "").split()
if _distributed_storage_preference:
    app.config["DISTRIBUTED_STORAGE_PREFERENCE"] = _distributed_storage_preference

# Generate a secret key if none was specified.
if app.config["SECRET_KEY"] is None:
    logger.debug("Generating in-memory secret key")
    app.config["SECRET_KEY"] = generate_secret_key()

# If the "preferred" scheme is https, then http is not allowed. Therefore, ensure we have a secure
# session cookie.
if app.config["PREFERRED_URL_SCHEME"] == "https" and not app.config.get(
    "FORCE_NONSECURE_SESSION_COOKIE", False
):
    app.config["SESSION_COOKIE_SECURE"] = True

# Load features from config.
features.import_features(app.config)

# Register additional experimental artifact types.
# TODO: extract this into a real, dynamic registration system.
if features.HELM_OCI_SUPPORT:
    HELM_CHART_CONFIG_TYPE = "application/vnd.cncf.helm.config.v1+json"
    HELM_CHART_LAYER_TYPES = ["application/tar+gzip"]
    register_artifact_type(HELM_CHART_CONFIG_TYPE, HELM_CHART_LAYER_TYPES)

CONFIG_DIGEST = hashlib.sha256(json.dumps(app.config, default=str).encode("utf-8")).hexdigest()[0:8]

logger.debug("Loaded config", extra={"config": app.config})


class RequestWithId(Request):
    request_gen = staticmethod(urn_generator(["request"]))

    def __init__(self, *args, **kwargs):
        super(RequestWithId, self).__init__(*args, **kwargs)
        self.request_id = self.request_gen()


@app.before_request
def _request_start():
    if os.getenv("PYDEV_DEBUG", None):
        import pydevd_pycharm

        host, port = os.getenv("PYDEV_DEBUG").split(":")
        pydevd_pycharm.settrace(
            host, port=int(port), stdoutToServer=True, stderrToServer=True, suspend=False,
        )

    logger.debug(
        "Starting request: %s (%s)",
        request.request_id,
        request.path,
        extra={"request_id": request.request_id},
    )


DEFAULT_FILTER = lambda x: "[FILTERED]"
FILTERED_VALUES = [
    {"key": ["password"], "fn": DEFAULT_FILTER},
    {"key": ["user", "password"], "fn": DEFAULT_FILTER},
    {"key": ["blob"], "fn": lambda x: x[0:8]},
]


@app.after_request
def _request_end(resp):
    try:
        jsonbody = request.get_json(force=True, silent=True)
    except HTTPException:
        jsonbody = None

    values = request.values.to_dict()

    if jsonbody and not isinstance(jsonbody, dict):
        jsonbody = {"_parsererror": jsonbody}

    if isinstance(values, dict):
        filter_logs(values, FILTERED_VALUES)

    extra = {
        "endpoint": request.endpoint,
        "request_id": request.request_id,
        "remote_addr": request.remote_addr,
        "http_method": request.method,
        "original_url": request.url,
        "path": request.path,
        "parameters": values,
        "json_body": jsonbody,
        "confsha": CONFIG_DIGEST,
    }

    if request.user_agent is not None:
        extra["user-agent"] = request.user_agent.string

    logger.debug("Ending request: %s (%s)", request.request_id, request.path, extra=extra)
    return resp


if app.config.get("GREENLET_TRACING", True):
    enable_tracing()


root_logger = logging.getLogger()

app.request_class = RequestWithId

# Register custom converters.
app.url_map.converters["regex"] = RegexConverter
app.url_map.converters["repopath"] = RepositoryPathConverter
app.url_map.converters["apirepopath"] = APIRepositoryPathConverter

Principal(app, use_sessions=False)

tf = app.config["DB_TRANSACTION_FACTORY"]

model_cache = get_model_cache(app.config)
avatar = Avatar(app)
login_manager = LoginManager(app)
mail = Mail(app)
prometheus = PrometheusPlugin(app)
chunk_cleanup_queue = WorkQueue(app.config["CHUNK_CLEANUP_QUEUE_NAME"], tf)
instance_keys = InstanceKeys(app)
ip_resolver = IPResolver(app)
storage = Storage(app, chunk_cleanup_queue, instance_keys, config_provider, ip_resolver)
userfiles = Userfiles(app, storage)
log_archive = LogArchive(app, storage)
analytics = Analytics(app)
billing = Billing(app)
sentry = Sentry(app)
build_logs = BuildLogs(app)
authentication = UserAuthentication(app, config_provider, OVERRIDE_CONFIG_DIRECTORY)
userevents = UserEventsBuilderModule(app)
superusers = SuperUserManager(app)
instance_keys = InstanceKeys(app)
label_validator = LabelValidator(app)
build_canceller = BuildCanceller(app)

github_trigger = GithubOAuthService(app.config, "GITHUB_TRIGGER_CONFIG")
gitlab_trigger = GitLabOAuthService(app.config, "GITLAB_TRIGGER_CONFIG")

oauth_login = OAuthLoginManager(app.config)
oauth_apps = [github_trigger, gitlab_trigger]

image_replication_queue = WorkQueue(app.config["REPLICATION_QUEUE_NAME"], tf, has_namespace=False)
dockerfile_build_queue = WorkQueue(
    app.config["DOCKERFILE_BUILD_QUEUE_NAME"], tf, has_namespace=True
)
notification_queue = WorkQueue(app.config["NOTIFICATION_QUEUE_NAME"], tf, has_namespace=True)
secscan_notification_queue = WorkQueue(
    app.config["SECSCAN_V4_NOTIFICATION_QUEUE_NAME"], tf, has_namespace=False
)
export_action_logs_queue = WorkQueue(
    app.config["EXPORT_ACTION_LOGS_QUEUE_NAME"], tf, has_namespace=True
)

repository_gc_queue = WorkQueue(app.config["REPOSITORY_GC_QUEUE_NAME"], tf, has_namespace=True)

# Note: We set `has_namespace` to `False` here, as we explicitly want this queue to not be emptied
# when a namespace is marked for deletion.
namespace_gc_queue = WorkQueue(app.config["NAMESPACE_GC_QUEUE_NAME"], tf, has_namespace=False)

all_queues = [
    image_replication_queue,
    dockerfile_build_queue,
    notification_queue,
    chunk_cleanup_queue,
    repository_gc_queue,
    namespace_gc_queue,
]

url_scheme_and_hostname = URLSchemeAndHostname(
    app.config["PREFERRED_URL_SCHEME"], app.config["SERVER_HOSTNAME"]
)

repo_mirror_api = RepoMirrorAPI(
    app.config,
    app.config["SERVER_HOSTNAME"],
    app.config["HTTPCLIENT"],
    instance_keys=instance_keys,
)

tuf_metadata_api = TUFMetadataAPI(app, app.config)

# Check for a key in config. If none found, generate a new signing key for Docker V2 manifests.
_v2_key_path = os.path.join(OVERRIDE_CONFIG_DIRECTORY, DOCKER_V2_SIGNINGKEY_FILENAME)
if os.path.exists(_v2_key_path):
    docker_v2_signing_key = RSAKey().load(_v2_key_path)
else:
    docker_v2_signing_key = RSAKey(key=RSA.generate(2048))

# Configure the database.
if app.config.get("DATABASE_SECRET_KEY") is None and app.config.get("SETUP_COMPLETE", False):
    raise Exception("Missing DATABASE_SECRET_KEY in config; did you perhaps forget to add it?")


database.configure(app.config)

model.config.app_config = app.config
model.config.store = storage
model.config.register_repo_cleanup_callback(tuf_metadata_api.delete_metadata)

secscan_model.configure(app, instance_keys, storage)

logs_model.configure(app.config)

# NOTE: We re-use the page token key here as this is just to obfuscate IDs for V1, and
# does not need to actually be secure.
registry_model.set_id_hash_salt(app.config.get("PAGE_TOKEN_KEY"))


@login_manager.user_loader
def load_user(user_uuid):
    logger.debug("User loader loading deferred user with uuid: %s", user_uuid)
    return LoginWrappedDBUser(user_uuid)


get_app_url = partial(get_app_url, app.config)
