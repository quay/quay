import base64
import os
import json
import uuid

import pytest

from contextlib import contextmanager
from collections import namedtuple
from httmock import urlmatch, HTTMock

from util.config.provider import KubernetesConfigProvider


def normalize_path(path):
    return path.replace("/", "_")


@contextmanager
def fake_kubernetes_api(tmpdir_factory, files=None):
    hostname = "kubapi"
    service_account_token_path = str(tmpdir_factory.mktemp("k8s").join("serviceaccount"))
    auth_header = str(uuid.uuid4())

    with open(service_account_token_path, "w") as f:
        f.write(auth_header)

    global secret
    secret = {"data": {}}

    def write_file(config_dir, filepath, value):
        normalized_path = normalize_path(filepath)
        absolute_path = str(config_dir.join(normalized_path))
        try:
            os.makedirs(os.path.dirname(absolute_path))
        except OSError:
            pass

        with open(absolute_path, "w") as f:
            f.write(value)

    config_dir = tmpdir_factory.mktemp("config")
    if files:
        for filepath, value in files.items():
            normalized_path = normalize_path(filepath)
            write_file(config_dir, filepath, value)
            secret["data"][normalized_path] = base64.b64encode(value.encode("utf-8")).decode(
                "ascii"
            )

    @urlmatch(
        netloc=hostname,
        path="/api/v1/namespaces/quay-enterprise/secrets/quay-enterprise-config-secret$",
        method="get",
    )
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(secret)}

    @urlmatch(
        netloc=hostname,
        path="/api/v1/namespaces/quay-enterprise/secrets/quay-enterprise-config-secret$",
        method="put",
    )
    def put_secret(_, request):
        updated_secret = json.loads(request.body)
        for filepath, value in updated_secret["data"].items():
            if filepath not in secret["data"]:
                # Add
                write_file(
                    config_dir, filepath, base64.b64decode(value.encode("utf-8")).decode("ascii")
                )

        for filepath in secret["data"]:
            if filepath not in updated_secret["data"]:
                # Remove.
                normalized_path = normalize_path(filepath)
                os.remove(str(config_dir.join(normalized_path)))

        secret["data"] = updated_secret["data"]
        return {"status_code": 200, "content": json.dumps(secret)}

    @urlmatch(netloc=hostname, path="/api/v1/namespaces/quay-enterprise$")
    def get_namespace(_, __):
        return {"status_code": 200, "content": json.dumps({})}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        print(url)
        return {"status_code": 404, "content": "{}"}

    with HTTMock(get_secret, put_secret, get_namespace, catch_all):
        provider = KubernetesConfigProvider(
            str(config_dir),
            "config.yaml",
            "config.py",
            api_host=hostname,
            service_account_token_path=service_account_token_path,
        )

        # Validate all the files.
        for filepath, value in files.items():
            normalized_path = normalize_path(filepath)
            assert provider.volume_file_exists(normalized_path)
            with provider.get_volume_file(normalized_path) as f:
                assert f.read() == value

        yield provider


def test_basic_config(tmpdir_factory):
    basic_files = {
        "config.yaml": "FOO: bar",
    }

    with fake_kubernetes_api(tmpdir_factory, files=basic_files) as provider:
        assert provider.config_exists()
        assert provider.get_config() is not None
        assert provider.get_config()["FOO"] == "bar"


@pytest.mark.parametrize("filepath", ["foo", "foo/meh", "foo/bar/baz",])
def test_remove_file(filepath, tmpdir_factory):
    basic_files = {
        filepath: "foo",
    }

    with fake_kubernetes_api(tmpdir_factory, files=basic_files) as provider:
        normalized_path = normalize_path(filepath)
        assert provider.volume_file_exists(normalized_path)
        provider.remove_volume_file(normalized_path)
        assert not provider.volume_file_exists(normalized_path)


class TestFlaskFile(object):
    def save(self, buf):
        buf.write("hello world!")


def test_save_file(tmpdir_factory):
    basic_files = {}

    with fake_kubernetes_api(tmpdir_factory, files=basic_files) as provider:
        assert not provider.volume_file_exists("testfile")
        flask_file = TestFlaskFile()
        provider.save_volume_file(flask_file, "testfile")
        assert provider.volume_file_exists("testfile")
