import copy
import logging.config
import json
import os
import shutil

from tempfile import NamedTemporaryFile

import pytest

from Crypto import Random
from flask import jsonify, g
from flask_principal import Identity

from app import storage
from data.database import (
    close_db_filter,
    configure,
    QueueItem,
    ImageStorage,
    TagManifest,
    TagManifestToManifest,
    Manifest,
    ManifestLegacyImage,
    ManifestBlob,
    NamespaceGeoRestriction,
    User,
)
from data import model
from data.registry_model import registry_model
from endpoints.csrf import generate_csrf_token
from image.docker.schema2 import EMPTY_LAYER_BLOB_DIGEST
from util.log import logfile_path

from test.registry.liveserverfixture import LiveServerExecutor


@pytest.fixture()
def registry_server_executor(app):
    def generate_csrf():
        return generate_csrf_token()

    def set_supports_direct_download(enabled):
        storage.put_content(
            ["local_us"], "supports_direct_download", b"true" if enabled else b"false"
        )
        return "OK"

    def verify_replication_for(namespace, repo_name, tag_name):
        repo_ref = registry_model.lookup_repository(namespace, repo_name)
        assert repo_ref

        tag = registry_model.get_repo_tag(repo_ref, tag_name)
        assert tag

        manifest = registry_model.get_manifest_for_tag(tag)
        assert manifest

        for layer in registry_model.list_manifest_layers(manifest, storage):
            if layer.blob.digest != EMPTY_LAYER_BLOB_DIGEST:
                QueueItem.select().where(
                    QueueItem.queue_name ** ("%" + layer.blob.uuid + "%")
                ).get()

        return "OK"

    def set_feature(feature_name, value):
        import features
        from app import app

        old_value = features._FEATURES[feature_name].value
        features._FEATURES[feature_name].value = value
        app.config["FEATURE_%s" % feature_name] = value
        return jsonify({"old_value": old_value})

    def set_config_key(config_key, value):
        from app import app as current_app

        old_value = app.config.get(config_key)
        app.config[config_key] = value
        current_app.config[config_key] = value

        # Close any existing connection.
        close_db_filter(None)

        # Reload the database config.
        configure(app.config)

        return jsonify({"old_value": old_value})

    def clear_uncompressed_size(image_id):
        image = model.image.get_image_by_id("devtable", "newrepo", image_id)
        image.storage.uncompressed_size = None
        image.storage.save()
        return "OK"

    def add_token():
        another_token = model.token.create_delegate_token(
            "devtable", "newrepo", "my-new-token", "write"
        )
        return model.token.get_full_token_string(another_token)

    def break_database():
        # Close any existing connection.
        close_db_filter(None)

        # Reload the database config with an invalid connection.
        config = copy.copy(app.config)
        config["DB_URI"] = "sqlite:///not/a/valid/database"
        configure(config)

        return "OK"

    def reload_app(server_hostname):
        # Close any existing connection.
        close_db_filter(None)

        # Reload the database config.
        app.config["SERVER_HOSTNAME"] = server_hostname[len("http://") :]
        configure(app.config)

        # Reload random after the process split, as it cannot be used uninitialized across forks.
        Random.atfork()

        # Required for anonymous calls to not exception.
        g.identity = Identity(None, "none")

        if os.environ.get("DEBUGLOG") == "true":
            logging.config.fileConfig(logfile_path(debug=True), disable_existing_loggers=False)

        return "OK"

    def create_app_repository(namespace, name):
        user = model.user.get_user(namespace)
        model.repository.create_repository(namespace, name, user, repo_kind="application")
        return "OK"

    def disable_namespace(namespace):
        namespace_obj = model.user.get_namespace_user(namespace)
        namespace_obj.enabled = False
        namespace_obj.save()
        return "OK"

    def delete_manifests():
        ManifestLegacyImage.delete().execute()
        ManifestBlob.delete().execute()
        Manifest.delete().execute()
        TagManifestToManifest.delete().execute()
        TagManifest.delete().execute()
        return "OK"

    def set_geo_block_for_namespace(namespace_name, iso_country_code):
        NamespaceGeoRestriction.create(
            namespace=User.get(username=namespace_name),
            description="",
            unstructured_json={},
            restricted_region_iso_code=iso_country_code,
        )
        return "OK"

    executor = LiveServerExecutor()
    executor.register("generate_csrf", generate_csrf)
    executor.register("set_supports_direct_download", set_supports_direct_download)
    executor.register("verify_replication_for", verify_replication_for)
    executor.register("set_feature", set_feature)
    executor.register("set_config_key", set_config_key)
    executor.register("clear_uncompressed_size", clear_uncompressed_size)
    executor.register("add_token", add_token)
    executor.register("break_database", break_database)
    executor.register("reload_app", reload_app)
    executor.register("create_app_repository", create_app_repository)
    executor.register("disable_namespace", disable_namespace)
    executor.register("delete_manifests", delete_manifests)
    executor.register("set_geo_block_for_namespace", set_geo_block_for_namespace)
    return executor


@pytest.fixture(params=["oci_model"])
def data_model(request):
    return request.param


@pytest.fixture()
def liveserver_app(app, registry_server_executor, init_db_path, data_model):
    registry_server_executor.apply_blueprint_to_app(app)

    if os.environ.get("DEBUG", "false").lower() == "true":
        app.config["DEBUG"] = True

    # Copy the clean database to a new path. We cannot share the DB created by the
    # normal app fixture, as it is already open in the local process.
    local_db_file = NamedTemporaryFile(delete=True)
    local_db_file.close()

    shutil.copy2(init_db_path, local_db_file.name)
    app.config["DB_URI"] = "sqlite:///{0}".format(local_db_file.name)
    return app


@pytest.fixture()
def app_reloader(request, liveserver, registry_server_executor):
    registry_server_executor.on(liveserver).reload_app(liveserver.url)
    yield


class FeatureFlagValue(object):
    """
    Helper object which temporarily sets the value of a feature flag.

    Usage:

    with FeatureFlagValue('ANONYMOUS_ACCESS', False, registry_server_executor.on(liveserver)):
      ... Features.ANONYMOUS_ACCESS is False in this context ...
    """

    def __init__(self, feature_flag, test_value, executor):
        self.feature_flag = feature_flag
        self.test_value = test_value
        self.executor = executor

        self.old_value = None

    def __enter__(self):
        result = self.executor.set_feature(self.feature_flag, self.test_value)
        self.old_value = result.json()["old_value"]

    def __exit__(self, type, value, traceback):
        self.executor.set_feature(self.feature_flag, self.old_value)


class ConfigChange(object):
    """
    Helper object which temporarily sets the value of a config key.

    Usage:

    with ConfigChange('SOMEKEY', 'value', registry_server_executor.on(liveserver), liveserver):
      ... app.config['SOMEKEY'] is 'value' in this context ...
    """

    def __init__(self, config_key, test_value, executor, liveserver):
        self.config_key = config_key
        self.test_value = test_value
        self.executor = executor
        self.liveserver = liveserver

        self.old_value = None

    def __enter__(self):
        result = self.executor.set_config_key(self.config_key, self.test_value)
        self.old_value = result.json()["old_value"]

    def __exit__(self, type, value, traceback):
        self.executor.set_config_key(self.config_key, self.old_value)


class ApiCaller(object):
    def __init__(self, liveserver_session, registry_server_executor):
        self.liveserver_session = liveserver_session
        self.registry_server_executor = registry_server_executor

    def conduct_auth(self, username, password):
        r = self.post(
            "/api/v1/signin",
            data=json.dumps(dict(username=username, password=password)),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200

    def _adjust_params(self, kwargs):
        csrf_token = self.registry_server_executor.on_session(
            self.liveserver_session
        ).generate_csrf()

        if "params" not in kwargs:
            kwargs["params"] = {}

        kwargs["params"].update(
            {"_csrf_token": csrf_token,}
        )
        return kwargs

    def get(self, url, **kwargs):
        kwargs = self._adjust_params(kwargs)
        return self.liveserver_session.get(url, **kwargs)

    def post(self, url, **kwargs):
        kwargs = self._adjust_params(kwargs)
        return self.liveserver_session.post(url, **kwargs)

    def put(self, url, **kwargs):
        kwargs = self._adjust_params(kwargs)
        return self.liveserver_session.put(url, **kwargs)

    def delete(self, url, **kwargs):
        kwargs = self._adjust_params(kwargs)
        return self.liveserver_session.delete(url, **kwargs)

    def change_repo_visibility(self, namespace, repository, visibility):
        self.post(
            "/api/v1/repository/%s/%s/changevisibility" % (namespace, repository),
            data=json.dumps(dict(visibility=visibility)),
            headers={"Content-Type": "application/json"},
        )


@pytest.fixture(scope="function")
def api_caller(liveserver, registry_server_executor):
    return ApiCaller(liveserver.new_session(), registry_server_executor)
