import hashlib
import json
import logging
import os

from authlib.jose import JsonWebKey
from flask import request, Request
from flask_login import LoginManager
from flask_principal import Principal
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException

import features

from _init import (
    IS_KUBERNETES,
    IS_TESTING,
    OVERRIDE_CONFIG_DIRECTORY,
    IS_BUILDING,
)

from buildman.manager.buildcanceller import BuildCanceller
from data import database
from data.archivedlogs import LogArchive
from data.billing import Billing
from data.buildlogs import BuildLogs
from data.cache import get_model_cache
from data.model.user import LoginWrappedDBUser
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
    RepositoryPathRedirectConverter,
    V1CreateRepositoryPathConverter,
)
from oauth.services.github import GithubOAuthService
from oauth.services.gitlab import GitLabOAuthService
from oauth.loginmanager import OAuthLoginManager
from util.log import filter_logs
from util.saas.analytics import Analytics
from util.saas.exceptionlog import Sentry
from util.names import urn_generator
from util.config import URLSchemeAndHostname
from util.config.superusermanager import SuperUserManager
from util.label_validator import LabelValidator
from util.metrics.prometheus import PrometheusPlugin
from util.repomirror.api import RepoMirrorAPI
from util.greenlet_tracing import enable_tracing

from singletons.app import _app as app
from singletons.config import config_provider, get_app_url  # also initialize app.config
from singletons.workqueues import *  # noqa: F401, F403

# Initialize app
from singletons.avatar import avatar
from singletons.instance_keys import instance_keys
from singletons.ip_resolver import ip_resolver
from singletons.mail import mail
from singletons.storage import storage
from singletons.tuf_metadata_api import tuf_metadata_api

OVERRIDE_CONFIG_YAML_FILENAME = os.path.join(OVERRIDE_CONFIG_DIRECTORY, "config.yaml")
OVERRIDE_CONFIG_PY_FILENAME = os.path.join(OVERRIDE_CONFIG_DIRECTORY, "config.py")

DOCKER_V2_SIGNINGKEY_FILENAME = "docker_v2.pem"
INIT_SCRIPTS_LOCATION = "/conf/init/"

logger = logging.getLogger(__name__)

# Instantiate the configuration.
is_testing = IS_TESTING
is_kubernetes = IS_KUBERNETES
is_building = IS_BUILDING

if not is_testing:
    app.teardown_request(database.close_db_filter)

# Fix remote address handling for Flask.
if app.config.get("PROXY_COUNT", 1):
    app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=app.config.get("PROXY_COUNT", 1))

# Register additional experimental artifact types.
# TODO: extract this into a real, dynamic registration system.
if features.GENERAL_OCI_SUPPORT:
    for media_type, layer_types in app.config.get("ALLOWED_OCI_ARTIFACT_TYPES").items():
        register_artifact_type(media_type, layer_types)

if features.HELM_OCI_SUPPORT:
    HELM_CHART_CONFIG_TYPE = "application/vnd.cncf.helm.config.v1+json"
    HELM_CHART_LAYER_TYPES = [
        "application/tar+gzip",
        "application/vnd.cncf.helm.chart.content.v1.tar+gzip",
    ]
    register_artifact_type(HELM_CHART_CONFIG_TYPE, HELM_CHART_LAYER_TYPES)

CONFIG_DIGEST = hashlib.sha256(json.dumps(app.config, default=str).encode("utf-8")).hexdigest()[0:8]


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
            host,
            port=int(port),
            stdoutToServer=True,
            stderrToServer=True,
            suspend=False,
        )

    debug_extra = {}
    x_forwarded_for = request.headers.get("X-Forwarded-For", None)
    if x_forwarded_for is not None:
        debug_extra["X-Forwarded-For"] = x_forwarded_for

    logger.debug("Starting request: %s (%s) %s", request.request_id, request.path, debug_extra)


DEFAULT_FILTER = lambda x: "[FILTERED]"
FILTERED_VALUES = [
    {"key": ["password"], "fn": DEFAULT_FILTER},
    {"key": ["upstream_registry_password"], "fn": DEFAULT_FILTER},
    {"key": ["upstream_registry_username"], "fn": DEFAULT_FILTER},
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

    if isinstance(jsonbody, dict):
        filter_logs(jsonbody, FILTERED_VALUES)

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

    logger.debug("Ending request: %s (%s) %s", request.request_id, request.path, extra)
    return resp


if app.config.get("GREENLET_TRACING", True):
    enable_tracing()

root_logger = logging.getLogger()

app.request_class = RequestWithId

# Register custom converters.
app.url_map.converters["regex"] = RegexConverter
app.url_map.converters["repopath"] = RepositoryPathConverter
app.url_map.converters["apirepopath"] = APIRepositoryPathConverter
app.url_map.converters["repopathredirect"] = RepositoryPathRedirectConverter
app.url_map.converters["v1createrepopath"] = V1CreateRepositoryPathConverter

Principal(app, use_sessions=False)

tf = app.config["DB_TRANSACTION_FACTORY"]

model_cache = get_model_cache(app.config)
login_manager = LoginManager(app)
prometheus = PrometheusPlugin(app)
userfiles = Userfiles(app, storage)
log_archive = LogArchive(app, storage)
analytics = Analytics(app)
billing = Billing(app)
sentry = Sentry(app)
build_logs = BuildLogs(app)
authentication = UserAuthentication(app, config_provider, OVERRIDE_CONFIG_DIRECTORY)
userevents = UserEventsBuilderModule(app)
superusers = SuperUserManager(app)
label_validator = LabelValidator(app)
build_canceller = BuildCanceller(app)

github_trigger = GithubOAuthService(app.config, "GITHUB_TRIGGER_CONFIG")
gitlab_trigger = GitLabOAuthService(app.config, "GITLAB_TRIGGER_CONFIG")

oauth_login = OAuthLoginManager(app.config)
oauth_apps = [github_trigger, gitlab_trigger]


url_scheme_and_hostname = URLSchemeAndHostname(
    app.config["PREFERRED_URL_SCHEME"], app.config["SERVER_HOSTNAME"]
)

repo_mirror_api = RepoMirrorAPI(
    app.config,
    app.config["SERVER_HOSTNAME"],
    app.config["HTTPCLIENT"],
    instance_keys=instance_keys,
)

# Check for a key in config. If none found, generate a new signing key for Docker V2 manifests.
_v2_key_path = os.path.join(OVERRIDE_CONFIG_DIRECTORY, DOCKER_V2_SIGNINGKEY_FILENAME)
if os.path.exists(_v2_key_path):
    with open(_v2_key_path) as key_file:
        docker_v2_signing_key = JsonWebKey.import_key(key_file.read())
else:
    docker_v2_signing_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)

# Configure the database.
if app.config.get("DATABASE_SECRET_KEY") is None and app.config.get("SETUP_COMPLETE", False):
    raise Exception("Missing DATABASE_SECRET_KEY in config; did you perhaps forget to add it?")

secscan_model.configure(app, instance_keys, storage)

# NOTE: We re-use the page token key here as this is just to obfuscate IDs for V1, and
# does not need to actually be secure.
registry_model.set_id_hash_salt(app.config.get("PAGE_TOKEN_KEY"))


@login_manager.user_loader
def load_user(user_uuid):
    logger.debug("User loader loading deferred user with uuid: %s", user_uuid)
    return LoginWrappedDBUser(user_uuid)
