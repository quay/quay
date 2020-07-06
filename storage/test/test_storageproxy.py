import os

import pytest
import requests

from flask import Flask
from flask_testing import LiveServerTestCase

from storage import Storage
from util.security.instancekeys import InstanceKeys

from test.registry.liveserverfixture import *
from test.fixtures import *


@pytest.fixture(params=[True, False])
def is_proxying_enabled(request):
    return request.param


@pytest.fixture()
def server_executor(app):
    def reload_app(server_hostname):
        # Close any existing connection.
        close_db_filter(None)

        # Reload the database config.
        app.config["SERVER_HOSTNAME"] = server_hostname[len("http://") :]
        configure(app.config)
        return "OK"

    executor = LiveServerExecutor()
    executor.register("reload_app", reload_app)
    return executor


@pytest.fixture()
def liveserver_app(app, server_executor, init_db_path, is_proxying_enabled):
    server_executor.apply_blueprint_to_app(app)

    if os.environ.get("DEBUG") == "true":
        app.config["DEBUG"] = True

    app.config["TESTING"] = True
    app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = "test/data/test.kid"
    app.config["INSTANCE_SERVICE_KEY_LOCATION"] = "test/data/test.pem"
    app.config["INSTANCE_SERVICE_KEY_SERVICE"] = "quay"

    app.config["FEATURE_PROXY_STORAGE"] = is_proxying_enabled

    app.config["DISTRIBUTED_STORAGE_CONFIG"] = {
        "test": ["FakeStorage", {}],
    }
    app.config["DISTRIBUTED_STORAGE_PREFERENCE"] = ["test"]
    return app


@pytest.fixture()
def instance_keys(liveserver_app):
    return InstanceKeys(liveserver_app)


@pytest.fixture()
def storage(liveserver_app, instance_keys):
    return Storage(liveserver_app, instance_keys=instance_keys)


@pytest.fixture()
def app_reloader(liveserver, server_executor):
    server_executor.on(liveserver).reload_app(liveserver.url)
    yield


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI") is not None, reason="not supported for non SQLite testing"
)
def test_storage_proxy_auth(
    storage, liveserver_app, liveserver_session, is_proxying_enabled, app_reloader
):
    # Activate direct download on the fake storage.
    storage.put_content(["test"], "supports_direct_download", b"true")

    # Get the unwrapped URL.
    direct_download_url = storage.get_direct_download_url(["test"], "somepath")
    proxy_index = direct_download_url.find("/_storage_proxy/")
    if is_proxying_enabled:
        assert proxy_index >= 0
    else:
        assert proxy_index == -1

    # Ensure that auth returns the expected value.
    headers = {
        "X-Original-URI": direct_download_url[proxy_index:] if proxy_index else "someurihere"
    }

    resp = liveserver_session.get("_storage_proxy_auth", headers=headers)
    assert resp.status_code == (500 if not is_proxying_enabled else 200)
