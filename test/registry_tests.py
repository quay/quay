import binascii
import copy
import hashlib
import json
import logging
import math
import os
import pytest
import random
import shutil
import string
import tarfile
import time
import unittest
import uuid

from io import StringIO
from tempfile import NamedTemporaryFile

import bencode
import gpgme
import requests
import resumablehashlib

from Crypto import Random
from Crypto.PublicKey import RSA
from flask import request, jsonify
from flask.blueprints import Blueprint
from flask_testing import LiveServerTestCase
from jwkest.jwk import RSAKey

import endpoints.decorated  # required for side effect

from app import app, storage, instance_keys, get_app_url
from .data.database import close_db_filter, configure, DerivedStorageForImage, QueueItem, Image
from .data import model
from digest.checksums import compute_simple
from endpoints.api import api_bp
from endpoints.csrf import generate_csrf_token
from endpoints.v1 import v1_bp
from endpoints.v2 import v2_bp
from endpoints.verbs import verbs
from image.docker.schema1 import DockerSchema1ManifestBuilder
from initdb import wipe_database, initialize_database, populate_database
from jsonschema import validate as validate_schema
from util.security.registry_jwt import decode_bearer_header
from util.timedeltastring import convert_to_timedelta


try:
    app.register_blueprint(v1_bp, url_prefix="/v1")
    app.register_blueprint(v2_bp, url_prefix="/v2")
    app.register_blueprint(verbs, url_prefix="/c1")
    app.register_blueprint(api_bp, url_prefix="/api")
except ValueError:
    # Blueprint was already registered
    pass


# Add a test blueprint for generating CSRF tokens, setting feature flags and reloading the
# DB connection.

testbp = Blueprint("testbp", __name__)
logger = logging.getLogger(__name__)


@testbp.route("/csrf", methods=["GET"])
def generate_csrf():
    return generate_csrf_token()


@testbp.route("/fakestoragedd/<enabled>", methods=["POST"])
def set_fakestorage_directdownload(enabled):
    storage.put_content(["local_us"], "supports_direct_download", enabled)
    return "OK"


@testbp.route("/deleteimage/<image_id>", methods=["POST"])
def delete_image(image_id):
    image = Image.get(docker_image_id=image_id)
    image.docker_image_id = "DELETED"
    image.save()
    return "OK"


@testbp.route("/storagerepentry/<image_id>", methods=["GET"])
def get_storage_replication_entry(image_id):
    image = Image.get(docker_image_id=image_id)
    QueueItem.select().where(QueueItem.queue_name ** ("%" + image.storage.uuid + "%")).get()
    return "OK"


@testbp.route("/feature/<feature_name>", methods=["POST"])
def set_feature(feature_name):
    import features

    old_value = features._FEATURES[feature_name].value
    features._FEATURES[feature_name].value = request.get_json()["value"]
    return jsonify({"old_value": old_value})


@testbp.route("/clearderivedcache", methods=["POST"])
def clearderivedcache():
    DerivedStorageForImage.delete().execute()
    return "OK"


@testbp.route("/removeuncompressed/<image_id>", methods=["POST"])
def removeuncompressed(image_id):
    image = model.image.get_image_by_id("devtable", "newrepo", image_id)
    image.storage.uncompressed_size = None
    image.storage.save()
    return "OK"


@testbp.route("/addtoken", methods=["POST"])
def addtoken():
    another_token = model.token.create_delegate_token(
        "devtable", "newrepo", "my-new-token", "write"
    )
    another_token.code = "somecooltokencode"
    another_token.save()
    return "OK"


@testbp.route("/breakdatabase", methods=["POST"])
def break_database():
    # Close any existing connection.
    close_db_filter(None)

    # Reload the database config with an invalid connection.
    config = copy.copy(app.config)
    config["DB_URI"] = "sqlite:///not/a/valid/database"
    configure(config)

    return "OK"


@testbp.route("/reloadapp", methods=["POST"])
def reload_app():
    # Close any existing connection.
    close_db_filter(None)

    # Reload the database config.
    configure(app.config)

    # Reload random after the process split, as it cannot be used uninitialized across forks.
    Random.atfork()
    return "OK"


app.register_blueprint(testbp, url_prefix="/__test")


class TestFeature(object):
    """
    Helper object which temporarily sets the value of a feature flag.
    """

    def __init__(self, test_case, feature_flag, test_value):
        self.test_case = test_case
        self.feature_flag = feature_flag
        self.test_value = test_value
        self.old_value = None

    def __enter__(self):
        result = self.test_case.conduct(
            "POST",
            "/__test/feature/" + self.feature_flag,
            data=json.dumps(dict(value=self.test_value)),
            headers={"Content-Type": "application/json"},
        )

        result_data = json.loads(result.text)
        self.old_value = result_data["old_value"]

    def __exit__(self, type, value, traceback):
        self.test_case.conduct(
            "POST",
            "/__test/feature/" + self.feature_flag,
            data=json.dumps(dict(value=self.old_value)),
            headers={"Content-Type": "application/json"},
        )


_CLEAN_DATABASE_PATH = None
_JWK = RSAKey(key=RSA.generate(2048))


class FailureCodes:
    """
    Defines tuples representing the HTTP status codes for various errors.

    The tuple is defined as ('errordescription', V1HTTPStatusCode, V2HTTPStatusCode).
    """

    UNAUTHENTICATED = ("unauthenticated", 401, 401)
    UNAUTHORIZED = ("unauthorized", 403, 401)
    INVALID_REGISTRY = ("invalidregistry", 404, 404)
    DOES_NOT_EXIST = ("doesnotexist", 404, 404)
    INVALID_REQUEST = ("invalidrequest", 400, 400)
    APP_REPOSITORY = ("apprepository", 405, 405)


def _get_expected_code(expected_failure, version, success_status_code):
    """
    Returns the HTTP status code for the expected failure under the specified protocol version (1 or
    2).

    If none, returns the success status code.
    """
    if not expected_failure:
        return success_status_code

    return expected_failure[version]


def _get_repo_name(namespace, name):
    if namespace == "":
        return name

    return "%s/%s" % (namespace, name)


def _get_full_contents(image_data, additional_fields=False):
    if "chunks" in image_data:
        # Data is just for chunking; no need for a real TAR.
        return image_data["contents"]

    layer_data = StringIO()

    def add_file(name, contents):
        tar_file_info = tarfile.TarInfo(name=name)
        tar_file_info.type = tarfile.REGTYPE
        tar_file_info.size = len(contents)
        tar_file_info.mtime = 1

        tar_file = tarfile.open(fileobj=layer_data, mode="w|gz")
        tar_file.addfile(tar_file_info, StringIO(contents))
        tar_file.close()

    add_file("contents", image_data["contents"])
    if additional_fields:
        add_file("anotherfile", str(uuid.uuid4()))

    layer_bytes = layer_data.getvalue()
    layer_data.close()

    return layer_bytes


def get_new_database_uri():
    # If a clean copy of the database has not yet been created, create one now.
    global _CLEAN_DATABASE_PATH
    if not _CLEAN_DATABASE_PATH:
        wipe_database()
        initialize_database()
        populate_database()
        close_db_filter(None)

        # Save the path of the clean database.
        _CLEAN_DATABASE_PATH = app.config["TEST_DB_FILE"].name

    # Create a new temp file to be used as the actual backing database for the test.
    # Note that we have the close() the file to ensure we can copy to it via shutil.
    local_db_file = NamedTemporaryFile(delete=True)
    local_db_file.close()

    # Copy the clean database to the path.
    shutil.copy2(_CLEAN_DATABASE_PATH, local_db_file.name)
    return "sqlite:///{0}".format(local_db_file.name)


class RegistryTestCaseMixin(LiveServerTestCase):
    def create_app(self):
        if os.environ.get("DEBUG") == "true":
            app.config["DEBUG"] = True

        app.config["TESTING"] = True
        app.config["LIVESERVER_PORT"] = 0  # LiveServerTestCase will choose the port for us.
        app.config["LIVESERVER_TIMEOUT"] = 15
        app.config["DB_URI"] = get_new_database_uri()
        return app

    def setUp(self):
        self.clearSession()

        # Tell the remote running app to reload the database and app. By default, the app forks from the
        # current context and has already loaded the DB config with the *original* DB URL. We call
        # the remote reload method to force it to pick up the changes to DB_URI set in the create_app
        # method.
        self.conduct("POST", "/__test/reloadapp")

    def clearSession(self):
        self.session = requests.Session()
        self.signature = None
        self.docker_token = "true"
        self.jwt = None

    def do_tag(self, namespace, repository, tag, image_id, expected_code=200, auth="sig"):
        repo_name = _get_repo_name(namespace, repository)
        self.conduct(
            "PUT",
            "/v1/repositories/%s/tags/%s" % (repo_name, tag),
            data='"%s"' % image_id,
            expected_code=expected_code,
            auth=auth,
        )

    def conduct_api_login(self, username, password):
        self.conduct(
            "POST",
            "/api/v1/signin",
            data=json.dumps(dict(username=username, password=password)),
            headers={"Content-Type": "application/json"},
        )

    def change_repo_visibility(self, namespace, repository, visibility):
        repo_name = _get_repo_name(namespace, repository)
        self.conduct(
            "POST",
            "/api/v1/repository/%s/changevisibility" % repo_name,
            data=json.dumps(dict(visibility=visibility)),
            headers={"Content-Type": "application/json"},
        )

    def assertContents(self, image_data, response):
        if "chunks" in image_data:
            return

        tar = tarfile.open(fileobj=StringIO(response.content))
        self.assertEqual(tar.extractfile("contents").read(), image_data["contents"])


class BaseRegistryMixin(object):
    def conduct(
        self,
        method,
        url,
        headers=None,
        data=None,
        auth=None,
        params=None,
        expected_code=200,
        json_data=None,
        user_agent=None,
    ):
        csrf_token = self._conduct("GET", "/__test/csrf").text
        return self._conduct(
            method,
            url,
            headers,
            data,
            auth,
            params,
            expected_code,
            json_data,
            user_agent,
            csrf_token=csrf_token,
        )

    def _conduct(
        self,
        method,
        url,
        headers=None,
        data=None,
        auth=None,
        params=None,
        expected_code=200,
        json_data=None,
        user_agent=None,
        csrf_token=None,
    ):
        params = params or {}
        if csrf_token:
            params["_csrf_token"] = csrf_token

        headers = headers or {}
        auth_tuple = None

        if user_agent is not None:
            headers["User-Agent"] = user_agent
        else:
            headers["User-Agent"] = "docker/1.9.1"

        if self.docker_token:
            headers["X-Docker-Token"] = self.docker_token

        if auth == "sig":
            if self.signature:
                headers["Authorization"] = "token " + self.signature
        elif auth == "jwt":
            if self.jwt:
                headers["Authorization"] = "Bearer " + self.jwt
        elif auth:
            auth_tuple = auth

        if json_data is not None:
            data = json.dumps(json_data)
            headers["Content-Type"] = "application/json"

        response = self.session.request(
            method,
            self.get_server_url() + url,
            headers=headers,
            data=data,
            auth=auth_tuple,
            params=params,
        )
        if expected_code is None:
            return response

        if response.status_code != expected_code:
            print(response.text)

        if "www-authenticate" in response.headers:
            self.signature = response.headers["www-authenticate"]

        if "X-Docker-Token" in response.headers:
            self.docker_token = response.headers["X-Docker-Token"]

        self.assertEqual(response.status_code, expected_code)
        return response

    def _get_default_images(self):
        return [{"id": "someid", "contents": "somecontent"}]


class V1RegistryMixin(BaseRegistryMixin):
    def v1_ping(self):
        self.conduct("GET", "/v1/_ping")


class V1RegistryPushMixin(V1RegistryMixin):
    push_version = "v1"

    def do_push(
        self,
        namespace,
        repository,
        username,
        password,
        images=None,
        expect_failure=None,
        munge_shas=[],
        tag_names=None,
        head_check=True,
    ):
        images = images or self._get_default_images()
        auth = (username, password)
        repo_name = _get_repo_name(namespace, repository)

        # Ping!
        self.v1_ping()

        # PUT /v1/repositories/{namespace}/{repository}/
        expected_code = _get_expected_code(expect_failure, 1, 201)
        self.conduct(
            "PUT",
            "/v1/repositories/%s/" % repo_name,
            data=json.dumps(images),
            auth=auth,
            expected_code=expected_code,
        )

        if expected_code != 201:
            return

        for image_data in images:
            image_id = image_data["id"]

            # PUT /v1/images/{imageID}/json
            image_json_data = {"id": image_id}
            if "size" in image_data:
                image_json_data["Size"] = image_data["size"]

            if "parent" in image_data:
                image_json_data["parent"] = image_data["parent"]

            self.conduct(
                "PUT", "/v1/images/%s/json" % image_id, data=json.dumps(image_json_data), auth="sig"
            )

            # PUT /v1/images/{imageID}/layer
            layer_bytes = _get_full_contents(image_data)
            self.conduct(
                "PUT", "/v1/images/%s/layer" % image_id, data=StringIO(layer_bytes), auth="sig"
            )

            # PUT /v1/images/{imageID}/checksum
            checksum = compute_simple(StringIO(layer_bytes), json.dumps(image_json_data))
            self.conduct(
                "PUT",
                "/v1/images/%s/checksum" % image_id,
                headers={"X-Docker-Checksum-Payload": checksum},
                auth="sig",
            )

        # PUT /v1/repositories/{namespace}/{repository}/tags/latest
        tag_names = tag_names or ["latest"]
        for tag_name in tag_names:
            self.do_tag(namespace, repository, tag_name, images[-1]["id"])

        # PUT /v1/repositories/{namespace}/{repository}/images
        self.conduct("PUT", "/v1/repositories/%s/images" % repo_name, expected_code=204, auth="sig")


class V1RegistryPullMixin(V1RegistryMixin):
    pull_version = "v1"

    def do_pull(
        self,
        namespace,
        repository,
        username=None,
        password="password",
        expect_failure=None,
        images=None,
        munge_shas=[],
    ):
        images = images or self._get_default_images()
        repo_name = _get_repo_name(namespace, repository)

        auth = None
        if username:
            auth = (username, password)

        # Ping!
        self.v1_ping()

        prefix = "/v1/repositories/%s/" % repo_name

        # GET /v1/repositories/{namespace}/{repository}/images
        expected_code = _get_expected_code(expect_failure, 1, 200)
        self.conduct("GET", prefix + "images", auth=auth, expected_code=expected_code)
        if expected_code != 200:
            return

        # GET /v1/repositories/{namespace}/{repository}/tags
        tags_result = json.loads(self.conduct("GET", prefix + "tags", auth="sig").text)
        self.assertEqual(1, len(list(tags_result.values())))

        tag_image_id = tags_result["latest"]
        if not munge_shas:
            # Ensure we have a matching image ID.
            known_ids = [item["id"] for item in images]
            self.assertTrue(tag_image_id in known_ids)

        # Retrieve the ancestry of the tag image.
        image_prefix = "/v1/images/%s/" % tag_image_id
        ancestors = self.conduct("GET", image_prefix + "ancestry", auth="sig").json()
        for index, image_id in enumerate(ancestors):
            # /v1/images/{imageID}/{ancestry, json, layer}
            image_prefix = "/v1/images/%s/" % image_id
            self.conduct("GET", image_prefix + "ancestry", auth="sig")

            response = self.conduct("GET", image_prefix + "json", auth="sig")
            self.assertEqual(image_id, response.json()["id"])

            # Ensure we can HEAD the image layer.
            self.conduct("HEAD", image_prefix + "layer", auth="sig")

            # And retrieve the layer data.
            response = self.conduct("GET", image_prefix + "layer", auth="sig")

            # Ensure we can parse the layer bytes and that they contain the contents.
            self.assertContents(images[len(images) - index - 1], response)


class V2RegistryMixin(BaseRegistryMixin):
    MANIFEST_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string",},
            "tag": {"type": "string",},
            "signatures": {"type": "array", "itemType": {"type": "object",},},
            "fsLayers": {
                "type": "array",
                "itemType": {
                    "type": "object",
                    "properties": {"blobSum": {"type": "string",},},
                    "required": "blobSum",
                },
            },
            "history": {
                "type": "array",
                "itemType": {
                    "type": "object",
                    "properties": {"v1Compatibility": {"type": "object",},},
                    "required": ["v1Compatibility"],
                },
            },
        },
        "required": ["name", "tag", "fsLayers", "history", "signatures"],
    }

    def v2_ping(self):
        response = self.conduct("GET", "/v2/", expected_code=200 if self.jwt else 401, auth="jwt")
        self.assertEqual(response.headers["Docker-Distribution-API-Version"], "registry/2.0")

    def do_auth(self, username, password, namespace, repository, expected_code=200, scopes=[]):
        auth = None
        if username and password:
            auth = (username, password)

        repo_name = _get_repo_name(namespace, repository)

        params = {
            "account": username,
            "service": app.config["SERVER_HOSTNAME"],
        }

        if scopes:
            params["scope"] = "repository:%s:%s" % (repo_name, ",".join(scopes))

        response = self.conduct(
            "GET", "/v2/auth", params=params, auth=auth, expected_code=expected_code
        )

        if expected_code == 200:
            response_json = json.loads(response.text)
            self.assertIsNotNone(response_json.get("token"))
            self.jwt = response_json["token"]

        return response


class V2RegistryPushMixin(V2RegistryMixin):
    push_version = "v2"

    def do_push(
        self,
        namespace,
        repository,
        username,
        password,
        images=None,
        tag_names=None,
        cancel=False,
        invalid=False,
        expect_failure=None,
        scopes=None,
        munge_shas=[],
        head_check=True,
    ):
        images = images or self._get_default_images()
        repo_name = _get_repo_name(namespace, repository)

        # Ping!
        self.v2_ping()

        # Auth. If the expected failure is an invalid registry, in V2 we'll receive that error from
        # the auth endpoint first, rather than just the V2 requests below.
        expected_auth_code = 200
        if expect_failure == FailureCodes.INVALID_REGISTRY:
            expected_auth_code = 400
        elif expect_failure == FailureCodes.APP_REPOSITORY:
            expected_auth_code = 405

        self.do_auth(
            username,
            password,
            namespace,
            repository,
            scopes=scopes or ["push", "pull"],
            expected_code=expected_auth_code,
        )
        if expected_auth_code != 200:
            return

        expected_code = _get_expected_code(expect_failure, 2, 404)
        tag_names = tag_names or ["latest"]

        manifests = {}
        full_contents = {}
        for image_data in reversed(images):
            image_id = image_data["id"]
            full_contents[image_id] = _get_full_contents(
                image_data, additional_fields=image_id in munge_shas
            )

        # Build a fake manifest.
        for tag_name in tag_names:
            builder = DockerSchema1ManifestBuilder(namespace, repository, tag_name)

            for image_data in reversed(images):
                checksum = "sha256:" + hashlib.sha256(full_contents[image_data["id"]]).hexdigest()
                if invalid:
                    checksum = "sha256:" + hashlib.sha256("foobarbaz").hexdigest()

                builder.add_layer(checksum, json.dumps(image_data))

            # Build the manifest.
            manifests[tag_name] = builder.build(_JWK)

        # Push the image's layers.
        checksums = {}
        for image_data in reversed(images):
            image_id = image_data["id"]
            layer_bytes = full_contents[image_data["id"]]
            chunks = image_data.get("chunks")

            # Layer data should not yet exist.
            checksum = "sha256:" + hashlib.sha256(layer_bytes).hexdigest()

            if head_check:
                self.conduct(
                    "HEAD", "/v2/%s/blobs/%s" % (repo_name, checksum), expected_code=404, auth="jwt"
                )

            # If we expected a non-404 status code, then the HEAD operation has failed and we cannot
            # continue performing the push.
            if expected_code != 404:
                return

            # Start a new upload of the layer data.
            response = self.conduct(
                "POST", "/v2/%s/blobs/uploads/" % repo_name, expected_code=202, auth="jwt"
            )

            upload_uuid = response.headers["Docker-Upload-UUID"]

            server_hostname = get_app_url()
            new_upload_location = response.headers["Location"]
            self.assertTrue(new_upload_location.startswith(server_hostname))

            # We need to make this relative just for the tests because the live server test
            # case modifies the port.
            location = response.headers["Location"][len(server_hostname) :]

            # PATCH the image data into the layer.
            if chunks is None:
                self.conduct("PATCH", location, data=layer_bytes, expected_code=204, auth="jwt")
            else:
                for chunk in chunks:
                    if len(chunk) == 3:
                        (start_byte, end_byte, expected_code) = chunk
                    else:
                        (start_byte, end_byte) = chunk
                        expected_code = 204

                    contents_chunk = layer_bytes[start_byte:end_byte]
                    self.conduct(
                        "PATCH",
                        location,
                        data=contents_chunk,
                        expected_code=expected_code,
                        auth="jwt",
                        headers={"Range": "bytes=%s-%s" % (start_byte, end_byte)},
                    )

                    if expected_code != 204:
                        return

                    # Retrieve the upload status at each point.
                    status_url = "/v2/%s/blobs/uploads/%s" % (repo_name, upload_uuid)
                    response = self.conduct(
                        "GET",
                        status_url,
                        expected_code=204,
                        auth="jwt",
                        headers=dict(host=self.get_server_url()),
                    )
                    self.assertEqual(response.headers["Docker-Upload-UUID"], upload_uuid)
                    self.assertEqual(response.headers["Range"], "bytes=0-%s" % end_byte)

            if cancel:
                self.conduct(
                    "DELETE", location, params=dict(digest=checksum), expected_code=204, auth="jwt"
                )

                # Ensure the upload was canceled.
                status_url = "/v2/%s/blobs/uploads/%s" % (repo_name, upload_uuid)
                self.conduct(
                    "GET",
                    status_url,
                    expected_code=404,
                    auth="jwt",
                    headers=dict(host=self.get_server_url()),
                )
                return

            # Finish the layer upload with a PUT.
            response = self.conduct(
                "PUT", location, params=dict(digest=checksum), expected_code=201, auth="jwt"
            )

            self.assertEqual(response.headers["Docker-Content-Digest"], checksum)
            checksums[image_id] = checksum

            # Ensure the layer exists now.
            response = self.conduct(
                "HEAD", "/v2/%s/blobs/%s" % (repo_name, checksum), expected_code=200, auth="jwt"
            )
            self.assertEqual(response.headers["Docker-Content-Digest"], checksum)
            self.assertEqual(response.headers["Content-Length"], str(len(layer_bytes)))

        for tag_name in tag_names:
            manifest = manifests[tag_name]

            # Write the manifest. If we expect it to be invalid, we expect a 400 code. Otherwise, we expect
            # a 202 response for success.
            put_code = 400 if invalid else 202
            self.conduct(
                "PUT",
                "/v2/%s/manifests/%s" % (repo_name, tag_name),
                data=manifest.bytes.as_encoded_str(),
                expected_code=put_code,
                headers={"Content-Type": "application/json"},
                auth="jwt",
            )

        return checksums, manifests


class V2RegistryPullMixin(V2RegistryMixin):
    pull_version = "v2"

    def do_pull(
        self,
        namespace,
        repository,
        username=None,
        password="password",
        expect_failure=None,
        manifest_id=None,
        images=None,
        munge_shas=[],
    ):
        images = images or self._get_default_images()
        repo_name = _get_repo_name(namespace, repository)

        # Ping!
        self.v2_ping()

        # Auth. If the failure expected is unauthenticated, then the auth endpoint will 401 before
        # we reach any of the registry operations.
        expected_auth_code = 200
        if expect_failure == FailureCodes.UNAUTHENTICATED:
            expected_auth_code = 401
        elif expect_failure == FailureCodes.APP_REPOSITORY:
            expected_auth_code = 405

        self.do_auth(
            username,
            password,
            namespace,
            repository,
            scopes=["pull"],
            expected_code=expected_auth_code,
        )
        if expected_auth_code != 200:
            return

        # Retrieve the manifest for the tag or digest.
        manifest_id = manifest_id or "latest"

        expected_code = _get_expected_code(expect_failure, 2, 200)
        response = self.conduct(
            "GET",
            "/v2/%s/manifests/%s" % (repo_name, manifest_id),
            auth="jwt",
            expected_code=expected_code,
        )
        if expected_code != 200:
            return

        manifest_data = json.loads(response.text)

        # Ensure the manifest returned by us is valid.
        validate_schema(manifest_data, V2RegistryMixin.MANIFEST_SCHEMA)

        # Verify the layers.
        blobs = {}
        for index, layer in enumerate(reversed(manifest_data["fsLayers"])):
            blob_id = layer["blobSum"]
            result = self.conduct(
                "GET", "/v2/%s/blobs/%s" % (repo_name, blob_id), expected_code=200, auth="jwt"
            )

            blobs[blob_id] = result.content
            self.assertContents(images[index], result)

        # Verify the V1 metadata is present for each expected image.
        found_v1_layers = set()
        history = manifest_data["history"]
        for entry in history:
            v1_history = json.loads(entry["v1Compatibility"])
            found_v1_layers.add(v1_history["id"])

        for image in images:
            self.assertIn(image["id"], found_v1_layers)

        return blobs, manifest_data


class V1RegistryLoginMixin(object):
    def do_login(self, username, password, scope, expect_success=True):
        data = {
            "username": username,
            "password": password,
        }

        response = self.conduct("POST", "/v1/users/", json_data=data, expected_code=400)
        if expect_success:
            self.assertEqual(response.text, '"Username or email already exists"')
        else:
            self.assertNotEqual(response.text, '"Username or email already exists"')


class V2RegistryLoginMixin(object):
    def do_login(self, username, password, scope, expect_success=True, expected_failure_code=401):
        params = {
            "account": username,
            "scope": scope,
            "service": app.config["SERVER_HOSTNAME"],
        }

        if expect_success:
            expected_code = 200
        else:
            expected_code = expected_failure_code

        auth = None
        if username and password:
            auth = (username, password)

        response = self.conduct(
            "GET", "/v2/auth", params=params, auth=auth, expected_code=expected_code
        )
        return response


class RegistryTestsMixin(object):
    def test_previously_bad_repo_name(self):
        # Push a new repository with two layers.
        self.do_push("public", "foo.bar", "public", "password")

        # Pull the repository to verify.
        self.do_pull("public", "foo.bar", "public", "password")

    def test_middle_layer_different_sha(self):
        if self.push_version == "v1":
            # No SHAs to munge in V1.
            return

        images = [
            {"id": "rootid", "contents": "The root image",},
            {"id": "baseid", "contents": "The base image",},
        ]

        # Push a new repository with two layers.
        self.do_push("public", "newrepo", "public", "password", images=images)

        # Pull the repository to verify.
        self.do_pull("public", "newrepo", "public", "password", images=images)

        # Push again, munging the middle layer to ensure it gets assigned a different ID.
        images = [
            {"id": "rootid", "contents": "The root image",},
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        munged_shas = ["baseid"]

        # Push the repository.
        self.do_push(
            "public",
            "newrepo",
            "public",
            "password",
            images=images,
            munge_shas=munged_shas,
            head_check=False,
        )

        # Pull the repository to verify.
        self.do_pull(
            "public", "newrepo", "public", "password", images=images, munge_shas=munged_shas
        )

        # Ensures we don't hit weird tag overwrite issues.
        time.sleep(1)

        # Delete the baseid image.
        self.conduct("POST", "/__test/deleteimage/baseid")

        images = [
            {"id": "rootid", "contents": "The root image",},
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        # Push the repository again, this time munging the root layer. Since the baseid does not exist
        # anymore (since we deleted it above), this will have to look in the layer metadata itself
        # to work (which didn't before).
        munged_shas = ["rootid"]
        self.do_push(
            "public",
            "newrepo",
            "public",
            "password",
            images=images,
            munge_shas=munged_shas,
            head_check=False,
        )

        # Pull the repository to verify.
        self.do_pull(
            "public", "newrepo", "public", "password", images=images, munge_shas=munged_shas
        )

    def test_push_same_ids_different_base_sha(self):
        if self.push_version == "v1":
            # No SHAs to munge in V1.
            return

        images = [
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        munged_shas = ["baseid"]

        # Push a new repository.
        self.do_push("public", "newrepo", "public", "password", images=images)

        # Pull the repository.
        self.do_pull("public", "newrepo", "public", "password", images=images)

        # Push a the repository again, but with different SHAs.
        self.do_push(
            "public",
            "newrepo",
            "public",
            "password",
            images=images,
            munge_shas=munged_shas,
            head_check=False,
        )

        # Pull the repository.
        self.do_pull(
            "public", "newrepo", "public", "password", images=images, munge_shas=munged_shas
        )

    def test_push_same_ids_different_sha(self):
        if self.push_version == "v1":
            # No SHAs to munge in V1.
            return

        images = [
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        munged_shas = ["latestid"]

        # Push a new repository.
        self.do_push("public", "newrepo", "public", "password", images=images)

        # Pull the repository.
        self.do_pull("public", "newrepo", "public", "password", images=images)

        # Push a the repository again, but with different SHAs.
        self.do_push(
            "public",
            "newrepo",
            "public",
            "password",
            images=images,
            munge_shas=munged_shas,
            head_check=False,
        )

        # Pull the repository.
        self.do_pull(
            "public", "newrepo", "public", "password", images=images, munge_shas=munged_shas
        )

    def test_push_same_ids_different_sha_both_layers(self):
        if self.push_version == "v1":
            # No SHAs to munge in V1.
            return

        images = [
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        munged_shas = ["baseid", "latestid"]

        # Push a new repository.
        self.do_push("public", "newrepo", "public", "password", images=images)

        # Pull the repository.
        self.do_pull("public", "newrepo", "public", "password", images=images)

        # Push a the repository again, but with different SHAs.
        self.do_push(
            "public",
            "newrepo",
            "public",
            "password",
            images=images,
            munge_shas=munged_shas,
            head_check=False,
        )

        # Pull the repository.
        self.do_pull(
            "public", "newrepo", "public", "password", images=images, munge_shas=munged_shas
        )

    def test_push_same_ids_different_sha_with_unicode(self):
        if self.push_version == "v1":
            # No SHAs to munge in V1.
            return

        images = [
            {"id": "baseid", "contents": "The base image",},
            {
                "id": "latestid",
                "contents": "The latest image",
                "unicode": "the Pawe\xc5\x82 Kami\xc5\x84ski image",
                "parent": "baseid",
            },
        ]

        munged_shas = ["latestid", "baseid"]

        # Push a new repository.
        self.do_push("public", "newrepo", "public", "password", images=images)

        # Pull the repository.
        self.do_pull("public", "newrepo", "public", "password", images=images)

        # Push a the repository again, but with different SHAs.
        self.do_push(
            "public",
            "newrepo",
            "public",
            "password",
            images=images,
            munge_shas=munged_shas,
            head_check=False,
        )

        # Pull the repository.
        self.do_pull(
            "public", "newrepo", "public", "password", images=images, munge_shas=munged_shas
        )

    def test_push_pull_logging(self):
        # Push a new repository.
        self.do_push("public", "newrepo", "public", "password")

        # Retrieve the logs and ensure the push was added.
        self.conduct_api_login("public", "password")
        result = self.conduct("GET", "/api/v1/repository/public/newrepo/logs")
        logs = result.json()["logs"]

        self.assertEqual(1, len(logs))
        self.assertEqual("push_repo", logs[0]["kind"])
        self.assertEqual("public", logs[0]["metadata"]["namespace"])
        self.assertEqual("newrepo", logs[0]["metadata"]["repo"])
        self.assertEqual("public", logs[0]["performer"]["name"])

        # Pull the repository.
        self.do_pull("public", "newrepo", "public", "password")

        # Retrieve the logs and ensure the pull was added.
        result = self.conduct("GET", "/api/v1/repository/public/newrepo/logs")
        logs = result.json()["logs"]

        self.assertEqual(2, len(logs))
        self.assertEqual("pull_repo", logs[0]["kind"])
        self.assertEqual("public", logs[0]["performer"]["name"])

    def test_push_pull_logging_byrobot(self):
        # Lookup the robot's password.
        self.conduct_api_login("devtable", "password")
        resp = self.conduct("GET", "/api/v1/organization/buynlarge/robots/ownerbot")
        robot_token = json.loads(resp.text)["token"]

        # Push a new repository.
        self.do_push("buynlarge", "newrepo", "buynlarge+ownerbot", robot_token)

        # Retrieve the logs and ensure the push was added.
        result = self.conduct("GET", "/api/v1/repository/buynlarge/newrepo/logs")
        logs = result.json()["logs"]

        self.assertEqual(1, len(logs))
        self.assertEqual("push_repo", logs[0]["kind"])
        self.assertEqual("buynlarge", logs[0]["metadata"]["namespace"])
        self.assertEqual("newrepo", logs[0]["metadata"]["repo"])
        self.assertEqual("buynlarge+ownerbot", logs[0]["performer"]["name"])

        # Pull the repository.
        self.do_pull("buynlarge", "newrepo", "buynlarge+ownerbot", robot_token)

        # Retrieve the logs and ensure the pull was added.
        result = self.conduct("GET", "/api/v1/repository/buynlarge/newrepo/logs")
        logs = result.json()["logs"]

        self.assertEqual(2, len(logs))
        self.assertEqual("pull_repo", logs[0]["kind"])
        self.assertEqual("buynlarge", logs[0]["metadata"]["namespace"])
        self.assertEqual("newrepo", logs[0]["metadata"]["repo"])
        self.assertEqual("buynlarge+ownerbot", logs[0]["performer"]["name"])

    def test_pull_publicrepo_anonymous(self):
        # Add a new repository under the public user, so we have a real repository to pull.
        self.do_push("public", "newrepo", "public", "password")
        self.clearSession()

        # First try to pull the (currently private) repo anonymously, which should fail (since it is
        # private)
        self.do_pull("public", "newrepo", expect_failure=FailureCodes.UNAUTHORIZED)
        self.do_pull(
            "public", "newrepo", "devtable", "password", expect_failure=FailureCodes.UNAUTHORIZED
        )

        # Make the repository public.
        self.conduct_api_login("public", "password")
        self.change_repo_visibility("public", "newrepo", "public")
        self.clearSession()

        # Pull the repository anonymously, which should succeed because the repository is public.
        self.do_pull("public", "newrepo")

    def test_pull_publicrepo_devtable(self):
        # Add a new repository under the public user, so we have a real repository to pull.
        self.do_push("public", "newrepo", "public", "password")
        self.clearSession()

        # First try to pull the (currently private) repo as devtable, which should fail as it belongs
        # to public.
        self.do_pull(
            "public", "newrepo", "devtable", "password", expect_failure=FailureCodes.UNAUTHORIZED
        )

        # Make the repository public.
        self.conduct_api_login("public", "password")
        self.change_repo_visibility("public", "newrepo", "public")
        self.clearSession()

        # Pull the repository as devtable, which should succeed because the repository is public.
        self.do_pull("public", "newrepo", "devtable", "password")

    def test_pull_private_repo(self):
        # Add a new repository under the devtable user, so we have a real repository to pull.
        self.do_push("devtable", "newrepo", "devtable", "password")
        self.clearSession()

        # First try to pull the (currently private) repo as public, which should fail as it belongs
        # to devtable.
        self.do_pull(
            "devtable", "newrepo", "public", "password", expect_failure=FailureCodes.UNAUTHORIZED
        )

        # Pull the repository as devtable, which should succeed because the repository is owned by
        # devtable.
        self.do_pull("devtable", "newrepo", "devtable", "password")

    def test_public_no_anonymous_access_with_auth(self):
        # Turn off anonymous access.
        with TestFeature(self, "ANONYMOUS_ACCESS", False):
            # Add a new repository under the public user, so we have a real repository to pull.
            self.do_push("public", "newrepo", "public", "password")
            self.clearSession()

            # First try to pull the (currently private) repo as devtable, which should fail as it belongs
            # to public.
            self.do_pull(
                "public",
                "newrepo",
                "devtable",
                "password",
                expect_failure=FailureCodes.UNAUTHORIZED,
            )

            # Make the repository public.
            self.conduct_api_login("public", "password")
            self.change_repo_visibility("public", "newrepo", "public")
            self.clearSession()

            # Pull the repository as devtable, which should succeed because the repository is public.
            self.do_pull("public", "newrepo", "devtable", "password")

    def test_private_no_anonymous_access(self):
        # Turn off anonymous access.
        with TestFeature(self, "ANONYMOUS_ACCESS", False):
            # Add a new repository under the public user, so we have a real repository to pull.
            self.do_push("public", "newrepo", "public", "password")
            self.clearSession()

            # First try to pull the (currently private) repo as devtable, which should fail as it belongs
            # to public.
            self.do_pull(
                "public",
                "newrepo",
                "devtable",
                "password",
                expect_failure=FailureCodes.UNAUTHORIZED,
            )

            # Pull the repository as public, which should succeed because the repository is owned by public.
            self.do_pull("public", "newrepo", "public", "password")

    def test_public_no_anonymous_access_no_auth(self):
        # Turn off anonymous access.
        with TestFeature(self, "ANONYMOUS_ACCESS", False):
            # Add a new repository under the public user, so we have a real repository to pull.
            self.do_push("public", "newrepo", "public", "password")
            self.clearSession()

            # First try to pull the (currently private) repo as anonymous, which should fail as it
            # is private.
            self.do_pull("public", "newrepo", expect_failure=FailureCodes.UNAUTHENTICATED)

            # Make the repository public.
            self.conduct_api_login("public", "password")
            self.change_repo_visibility("public", "newrepo", "public")
            self.clearSession()

            # Try again to pull the (currently public) repo as anonymous, which should fail as
            # anonymous access is disabled.
            self.do_pull("public", "newrepo", expect_failure=FailureCodes.UNAUTHENTICATED)

            # Pull the repository as public, which should succeed because the repository is owned by public.
            self.do_pull("public", "newrepo", "public", "password")

            # Pull the repository as devtable, which should succeed because the repository is public.
            self.do_pull("public", "newrepo", "devtable", "password")

    def test_create_repo_creator_user(self):
        self.do_push("buynlarge", "newrepo", "creator", "password")

        # Pull the repository as creator, as they created it.
        self.do_pull("buynlarge", "newrepo", "creator", "password")

        # Pull the repository as devtable, which should succeed because the repository is owned by the
        # org.
        self.do_pull("buynlarge", "newrepo", "devtable", "password")

        # Attempt to pull the repository as reader, which should fail.
        self.do_pull(
            "buynlarge", "newrepo", "reader", "password", expect_failure=FailureCodes.UNAUTHORIZED
        )

    def test_create_repo_robot_owner(self):
        # Lookup the robot's password.
        self.conduct_api_login("devtable", "password")
        resp = self.conduct("GET", "/api/v1/organization/buynlarge/robots/ownerbot")
        robot_token = json.loads(resp.text)["token"]

        self.do_push("buynlarge", "newrepo", "buynlarge+ownerbot", robot_token)

        # Pull the repository as devtable, which should succeed because the repository is owned by the
        # org.
        self.do_pull("buynlarge", "newrepo", "devtable", "password")

    def test_create_repo_robot_creator(self):
        # Lookup the robot's password.
        self.conduct_api_login("devtable", "password")
        resp = self.conduct("GET", "/api/v1/organization/buynlarge/robots/creatorbot")
        robot_token = json.loads(resp.text)["token"]

        self.do_push("buynlarge", "newrepo", "buynlarge+creatorbot", robot_token)

        # Pull the repository as devtable, which should succeed because the repository is owned by the
        # org.
        self.do_pull("buynlarge", "newrepo", "devtable", "password")

    def test_library_repo(self):
        self.do_push("", "newrepo", "devtable", "password")
        self.do_pull("", "newrepo", "devtable", "password")
        self.do_pull("library", "newrepo", "devtable", "password")

    def test_library_disabled(self):
        with TestFeature(self, "LIBRARY_SUPPORT", False):
            self.do_push("library", "newrepo", "devtable", "password")
            self.do_pull("library", "newrepo", "devtable", "password")

    def test_image_replication(self):
        with TestFeature(self, "STORAGE_REPLICATION", True):
            images = [
                {"id": "baseid", "contents": "The base image",},
                {
                    "id": "latestid",
                    "contents": "The latest image",
                    "unicode": "the Pawe\xc5\x82 Kami\xc5\x84ski image",
                    "parent": "baseid",
                },
            ]

            # Push a new repository.
            self.do_push("public", "newrepo", "public", "password", images=images)

            # Ensure that we have a storage replication entry for each image pushed.
            self.conduct("GET", "/__test/storagerepentry/baseid", expected_code=200)
            self.conduct("GET", "/__test/storagerepentry/latestid", expected_code=200)


class V1RegistryTests(
    V1RegistryPullMixin,
    V1RegistryPushMixin,
    RegistryTestsMixin,
    RegistryTestCaseMixin,
    LiveServerTestCase,
):
    """
    Tests for V1 registry.
    """

    def test_search(self):
        # Public
        resp = self.conduct("GET", "/v1/search", params=dict(q="public"))
        data = resp.json()
        self.assertEqual(1, data["num_results"])
        self.assertEqual(1, len(data["results"]))

        # Simple (not logged in, no results)
        resp = self.conduct("GET", "/v1/search", params=dict(q="simple"))
        data = resp.json()
        self.assertEqual(0, data["num_results"])
        self.assertEqual(0, len(data["results"]))

        # Simple (logged in)
        resp = self.conduct(
            "GET", "/v1/search", params=dict(q="simple"), auth=("devtable", "password")
        )
        data = resp.json()
        self.assertEqual(1, data["num_results"])
        self.assertEqual(1, len(data["results"]))

    def test_search_pagination(self):
        # Check for the first page.
        resp = self.conduct(
            "GET", "/v1/search", params=dict(q="s", n="1"), auth=("devtable", "password")
        )
        data = resp.json()
        self.assertEqual("s", data["query"])

        self.assertEqual(1, data["num_results"])
        self.assertEqual(1, len(data["results"]))

        self.assertEqual(1, data["page"])
        self.assertTrue(data["num_pages"] > 1)

        # Check for the followup page.
        resp = self.conduct(
            "GET", "/v1/search", params=dict(q="s", n="1", page=2), auth=("devtable", "password")
        )
        data = resp.json()
        self.assertEqual("s", data["query"])

        self.assertEqual(1, data["num_results"])
        self.assertEqual(1, len(data["results"]))

        self.assertEqual(2, data["page"])

    def test_users(self):
        # Not logged in, should 404.
        self.conduct("GET", "/v1/users/", expected_code=404)

        # Try some logins.
        self.conduct("POST", "/v1/users/", json_data={"username": "freshuser"}, expected_code=400)
        resp = self.conduct(
            "POST",
            "/v1/users/",
            json_data={"username": "devtable", "password": "password"},
            expected_code=400,
        )

        # Because Docker
        self.assertEqual('"Username or email already exists"', resp.text)

    def test_push_reponame_with_slashes(self):
        # Attempt to add a repository name with slashes. This should fail as we do not support it.
        images = [{"id": "onlyimagehere", "contents": "somecontents",}]
        self.do_push(
            "public",
            "newrepo/somesubrepo",
            "public",
            "password",
            images,
            expect_failure=FailureCodes.INVALID_REGISTRY,
        )

    def test_push_unicode_metadata(self):
        self.conduct_api_login("devtable", "password")

        images = [
            {
                "id": "onlyimagehere",
                "comment": "Pawe\xc5\x82 Kami\xc5\x84ski <pawel.kaminski@codewise.com>".decode(
                    "utf-8"
                ),
                "contents": "somecontents",
            }
        ]

        self.do_push("devtable", "unicodetest", "devtable", "password", images)
        self.do_pull("devtable", "unicodetest", "devtable", "password", images=images)

    def test_tag_validation(self):
        image_id = "onlyimagehere"
        images = [{"id": image_id, "contents": "somecontents",}]

        self.do_push("public", "newrepo", "public", "password", images)
        self.do_tag("public", "newrepo", "1", image_id)
        self.do_tag("public", "newrepo", "x" * 128, image_id)
        self.do_tag("public", "newrepo", "", image_id, expected_code=404)
        self.do_tag("public", "newrepo", "x" * 129, image_id, expected_code=400)
        self.do_tag("public", "newrepo", ".fail", image_id, expected_code=400)
        self.do_tag("public", "newrepo", "-fail", image_id, expected_code=400)


class V2RegistryTests(
    V2RegistryPullMixin,
    V2RegistryPushMixin,
    RegistryTestsMixin,
    RegistryTestCaseMixin,
    LiveServerTestCase,
):
    """
    Tests for V2 registry.
    """

    def test_proper_auth_response(self):
        response = self.conduct(
            "GET", "/v2/devtable/doesnotexist/tags/list", auth="jwt", expected_code=401
        )
        self.assertIn("WWW-Authenticate", response.headers)
        self.assertIn(
            'scope="repository:devtable/doesnotexist:pull"', response.headers["WWW-Authenticate"]
        )

    def test_parent_misordered(self):
        images = [
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
            {"id": "baseid", "contents": "The base image",},
        ]

        self.do_push(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            images=images,
            expect_failure=FailureCodes.INVALID_REQUEST,
        )

    def test_invalid_parent(self):
        images = [
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "unknownparent",},
        ]

        self.do_push(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            images=images,
            expect_failure=FailureCodes.INVALID_REQUEST,
        )

    def test_tags_pagination(self):
        # Push 10 tags.
        tag_names = ["tag-%s" % i for i in range(0, 10)]
        self.do_push("public", "new-repo", "public", "password", tag_names=tag_names)

        encountered = set()

        # Ensure tags list is properly paginated.
        relative_url = "/v2/public/new-repo/tags/list?n=5"
        for i in range(0, 3):
            result = self.conduct("GET", relative_url, auth="jwt")
            result_json = result.json()
            encountered.update(set(result_json["tags"]))

            if "Link" not in result.headers:
                break

            # Check the next page of results.
            link_header = result.headers["Link"]
            self.assertTrue(link_header.startswith("<"))
            self.assertTrue(link_header.endswith('>; rel="next"'))

            link = link_header[1:]
            self.assertTrue(link.endswith('; rel="next"'))

            url, _ = link.split(";")
            relative_url = url[url.find("/v2/") : -1]

            encountered.update(set(result_json["tags"]))

        # Ensure we found all the results.
        self.assertEqual(encountered, set(tag_names))

    def test_numeric_tag(self):
        # Push a new repository.
        self.do_push("public", "new-repo", "public", "password", tag_names=["1234"])

        # Pull the repository.
        self.do_pull("public", "new-repo", "public", "password", manifest_id="1234")

    def test_label_invalid_manifest(self):
        images = [{"id": "someid", "config": {"Labels": None}, "contents": "somecontent"}]

        self.do_push("devtable", "newrepo", "devtable", "password", images=images)
        self.do_pull("devtable", "newrepo", "devtable", "password")

    def test_labels(self):
        # Push a new repo with the latest tag.
        images = [
            {
                "id": "someid",
                "config": {
                    "Labels": {"foo": "bar", "baz": "meh", "theoretically-invalid--label": "foo"}
                },
                "contents": "somecontent",
            }
        ]

        (_, manifests) = self.do_push("devtable", "newrepo", "devtable", "password", images=images)
        digest = manifests["latest"].digest

        self.conduct_api_login("devtable", "password")
        labels = self.conduct(
            "GET", "/api/v1/repository/devtable/newrepo/manifest/" + digest + "/labels"
        ).json()
        self.assertEqual(3, len(labels["labels"]))

        self.assertEqual("manifest", labels["labels"][0]["source_type"])
        self.assertEqual("manifest", labels["labels"][1]["source_type"])
        self.assertEqual("manifest", labels["labels"][2]["source_type"])

        self.assertEqual("text/plain", labels["labels"][0]["media_type"])
        self.assertEqual("text/plain", labels["labels"][1]["media_type"])
        self.assertEqual("text/plain", labels["labels"][2]["media_type"])

    def test_json_labels(self):
        # Push a new repo with the latest tag.
        images = [
            {
                "id": "someid",
                "config": {"Labels": {"foo": "bar", "baz": '{"some": "json"}'}},
                "contents": "somecontent",
            }
        ]

        (_, manifests) = self.do_push("devtable", "newrepo", "devtable", "password", images=images)
        digest = manifests["latest"].digest

        self.conduct_api_login("devtable", "password")
        labels = self.conduct(
            "GET", "/api/v1/repository/devtable/newrepo/manifest/" + digest + "/labels"
        ).json()
        self.assertEqual(2, len(labels["labels"]))

        media_types = set([label["media_type"] for label in labels["labels"]])

        self.assertTrue("text/plain" in media_types)
        self.assertTrue("application/json" in media_types)

    def test_not_json_labels(self):
        # Push a new repo with the latest tag.
        images = [
            {
                "id": "someid",
                "config": {"Labels": {"foo": "[hello world]", "bar": "{wassup?!}"}},
                "contents": "somecontent",
            }
        ]

        (_, manifests) = self.do_push("devtable", "newrepo", "devtable", "password", images=images)
        digest = manifests["latest"].digest

        self.conduct_api_login("devtable", "password")
        labels = self.conduct(
            "GET", "/api/v1/repository/devtable/newrepo/manifest/" + digest + "/labels"
        ).json()
        self.assertEqual(2, len(labels["labels"]))

        media_types = set([label["media_type"] for label in labels["labels"]])

        self.assertTrue("text/plain" in media_types)
        self.assertFalse("application/json" in media_types)

    def test_expiration_label(self):
        # Push a new repo with the latest tag.
        images = [
            {
                "id": "someid",
                "config": {"Labels": {"quay.expires-after": "1d"}},
                "contents": "somecontent",
            }
        ]

        (_, manifests) = self.do_push("devtable", "newrepo", "devtable", "password", images=images)

        self.conduct_api_login("devtable", "password")
        tags = self.conduct("GET", "/api/v1/repository/devtable/newrepo/tag").json()
        tag = tags["tags"][0]

        self.assertEqual(
            tag["end_ts"], tag["start_ts"] + convert_to_timedelta("1d").total_seconds()
        )

    def test_invalid_expiration_label(self):
        # Push a new repo with the latest tag.
        images = [
            {
                "id": "someid",
                "config": {"Labels": {"quay.expires-after": "blahblah"}},
                "contents": "somecontent",
            }
        ]

        (_, manifests) = self.do_push("devtable", "newrepo", "devtable", "password", images=images)

        self.conduct_api_login("devtable", "password")
        tags = self.conduct("GET", "/api/v1/repository/devtable/newrepo/tag").json()
        tag = tags["tags"][0]

        self.assertIsNone(tag.get("end_ts"))

    @pytest.mark.skipif(app.config["V3_UPGRADE_MODE"] == "complete", reason="Valid in V3")
    def test_invalid_manifest_type(self):
        namespace = "devtable"
        repository = "somerepo"
        tag_name = "sometag"

        repo_name = _get_repo_name(namespace, repository)

        self.v2_ping()
        self.do_auth("devtable", "password", namespace, repository, scopes=["push", "pull"])

        # Build a fake manifest.
        builder = DockerSchema1ManifestBuilder(namespace, repository, tag_name)
        builder.add_layer(
            "sha256:" + hashlib.sha256("invalid").hexdigest(), json.dumps({"id": "foo"})
        )
        manifest = builder.build(_JWK)

        self.conduct(
            "PUT",
            "/v2/%s/manifests/%s" % (repo_name, tag_name),
            data=manifest.bytes.as_encoded_str(),
            expected_code=415,
            headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
            auth="jwt",
        )

    def test_invalid_manifest(self):
        namespace = "devtable"
        repository = "somerepo"
        tag_name = "sometag"

        repo_name = _get_repo_name(namespace, repository)

        self.v2_ping()
        self.do_auth("devtable", "password", namespace, repository, scopes=["push", "pull"])

        self.conduct(
            "PUT",
            "/v2/%s/manifests/%s" % (repo_name, tag_name),
            data="{}",
            expected_code=400,
            auth="jwt",
        )

    @pytest.mark.skipif(app.config["V3_UPGRADE_MODE"] == "complete", reason="Valid in V3")
    def test_oci_manifest_type(self):
        namespace = "devtable"
        repository = "somerepo"
        tag_name = "sometag"

        repo_name = _get_repo_name(namespace, repository)

        self.v2_ping()
        self.do_auth("devtable", "password", namespace, repository, scopes=["push", "pull"])

        # Build a fake manifest.
        builder = DockerSchema1ManifestBuilder(namespace, repository, tag_name)
        builder.add_layer(
            "sha256:" + hashlib.sha256("invalid").hexdigest(), json.dumps({"id": "foo"})
        )
        manifest = builder.build(_JWK)

        self.conduct(
            "PUT",
            "/v2/%s/manifests/%s" % (repo_name, tag_name),
            data=manifest.bytes.as_encoded_str(),
            expected_code=415,
            headers={"Content-Type": "application/vnd.oci.image.manifest.v1+json"},
            auth="jwt",
        )

    def test_invalid_blob(self):
        namespace = "devtable"
        repository = "somerepo"
        tag_name = "sometag"

        repo_name = _get_repo_name(namespace, repository)

        self.v2_ping()
        self.do_auth("devtable", "password", namespace, repository, scopes=["push", "pull"])

        # Build a fake manifest.
        builder = DockerSchema1ManifestBuilder(namespace, repository, tag_name)
        builder.add_layer(
            "sha256:" + hashlib.sha256("invalid").hexdigest(), json.dumps({"id": "foo"})
        )
        manifest = builder.build(_JWK)

        response = self.conduct(
            "PUT",
            "/v2/%s/manifests/%s" % (repo_name, tag_name),
            data=manifest.bytes.as_encoded_str(),
            expected_code=400,
            headers={"Content-Type": "application/json"},
            auth="jwt",
        )
        self.assertEqual("MANIFEST_INVALID", response.json()["errors"][0]["code"])

    def test_delete_manifest(self):
        # Push a new repo with the latest tag.
        (_, manifests) = self.do_push("devtable", "newrepo", "devtable", "password")
        digest = manifests["latest"].digest

        # Ensure the pull works.
        self.do_pull("devtable", "newrepo", "devtable", "password")

        # Conduct auth for the write scope.
        self.do_auth("devtable", "password", "devtable", "newrepo", scopes=["push"])

        # Delete the digest.
        self.conduct(
            "DELETE", "/v2/devtable/newrepo/manifests/" + digest, auth="jwt", expected_code=202
        )

        # Ensure the tag no longer exists.
        self.do_pull(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            expect_failure=FailureCodes.DOES_NOT_EXIST,
        )

    def test_push_only_push_scope(self):
        images = [{"id": "onlyimagehere", "contents": "foobar",}]

        self.do_push("devtable", "somenewrepo", "devtable", "password", images, scopes=["push"])

    def test_push_reponame_with_slashes(self):
        # Attempt to add a repository name with slashes. This should fail as we do not support it.
        images = [{"id": "onlyimagehere", "contents": "somecontents",}]

        self.do_push(
            "public",
            "newrepo/somesubrepo",
            "devtable",
            "password",
            images,
            expect_failure=FailureCodes.INVALID_REGISTRY,
        )

    def test_invalid_push(self):
        self.do_push("devtable", "newrepo", "devtable", "password", invalid=True)

    def test_cancel_push(self):
        self.do_push("devtable", "newrepo", "devtable", "password", cancel=True)

    def test_with_blob_caching(self):
        # Add a repository and do a pull, to prime the cache.
        _, manifests = self.do_push("devtable", "newrepo", "devtable", "password")
        self.do_pull("devtable", "newrepo", "devtable", "password")

        # Purposefully break the database so that we can check if caching works.
        self.conduct("POST", "/__test/breakdatabase")

        # Attempt to pull the blobs and ensure we get back a result. Since the database is broken,
        # this will only work if caching is working and no additional queries/connections are made.
        repo_name = "devtable/newrepo"
        for tag_name in manifests:
            for layer in manifests[tag_name].layers:
                blob_id = str(layer.digest)
                self.conduct(
                    "GET", "/v2/%s/blobs/%s" % (repo_name, blob_id), expected_code=200, auth="jwt"
                )

    def test_pull_by_checksum(self):
        # Add a new repository under the user, so we have a real repository to pull.
        _, manifests = self.do_push("devtable", "newrepo", "devtable", "password")
        digest = manifests["latest"].digest

        # Attempt to pull by digest.
        self.do_pull("devtable", "newrepo", "devtable", "password", manifest_id=digest)

    def test_pull_invalid_image_tag(self):
        # Add a new repository under the user, so we have a real repository to pull.
        self.do_push("devtable", "newrepo", "devtable", "password")
        self.clearSession()

        # Attempt to pull the invalid tag.
        self.do_pull(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            manifest_id="invalid",
            expect_failure=FailureCodes.INVALID_REGISTRY,
        )

    def test_partial_upload_below_5mb(self):
        chunksize = 1024 * 1024 * 2
        size = chunksize * 3
        contents = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(size)
        )

        chunk_count = int(math.ceil((len(contents) * 1.0) / chunksize))
        chunks = [(index * chunksize, (index + 1) * chunksize) for index in range(chunk_count)]

        images = [{"id": "someid", "contents": contents, "chunks": chunks}]

        # Push the chunked upload.
        self.do_push("devtable", "newrepo", "devtable", "password", images=images)

        # Pull the image back and verify the contents.
        blobs, _ = self.do_pull("devtable", "newrepo", "devtable", "password", images=images)
        self.assertEqual(len(list(blobs.items())), 1)
        self.assertEqual(list(blobs.items())[0][1], contents)

    def test_partial_upload_way_below_5mb(self):
        size = 1024
        contents = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(size)
        )
        chunks = [(0, 100), (100, size)]

        images = [{"id": "someid", "contents": contents, "chunks": chunks}]

        # Push the chunked upload.
        self.do_push("devtable", "newrepo", "devtable", "password", images=images)

        # Pull the image back and verify the contents.
        blobs, _ = self.do_pull("devtable", "newrepo", "devtable", "password", images=images)
        self.assertEqual(len(list(blobs.items())), 1)
        self.assertEqual(list(blobs.items())[0][1], contents)

    def test_partial_upload_resend_below_5mb(self):
        size = 150
        contents = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(size)
        )

        chunks = [(0, 100), (10, size)]

        images = [{"id": "someid", "contents": contents, "chunks": chunks}]

        # Push the chunked upload.
        self.do_push("devtable", "newrepo", "devtable", "password", images=images)

        # Pull the image back and verify the contents.
        blobs, _ = self.do_pull("devtable", "newrepo", "devtable", "password", images=images)
        self.assertEqual(len(list(blobs.items())), 1)
        self.assertEqual(list(blobs.items())[0][1], contents)

    def test_partial_upload_try_resend_with_gap(self):
        size = 150
        contents = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(size)
        )

        chunks = [(0, 100), (101, size, 416)]

        images = [{"id": "someid", "contents": contents, "chunks": chunks}]

        # Attempt to push the chunked upload, which should fail.
        self.do_push("devtable", "newrepo", "devtable", "password", images=images)

    def test_multiple_layers_invalid(self):
        # Attempt to push a manifest with an image depending on an unknown base layer.
        images = [{"id": "latestid", "contents": "the latest image", "parent": "baseid",}]

        self.do_push(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            images=images,
            expect_failure=FailureCodes.INVALID_REQUEST,
        )

    def test_multiple_layers(self):
        # Push a manifest with multiple layers.
        images = [
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        self.do_push("devtable", "newrepo", "devtable", "password", images=images)

    def test_invalid_regname(self):
        self.do_push(
            "devtable",
            "this/is/a/repo",
            "devtable",
            "password",
            expect_failure=FailureCodes.INVALID_REGISTRY,
        )

    def test_multiple_tags(self):
        latest_images = [{"id": "latestid", "contents": "the latest image"}]

        foobar_images = [{"id": "foobarid", "contents": "the foobar image",}]

        # Create the repo.
        self.do_push(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            images=latest_images,
            tag_names=["latest"],
        )

        self.do_push(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            images=foobar_images,
            tag_names=["foobar"],
        )

        # Retrieve the tags.
        response = self.conduct(
            "GET", "/v2/devtable/newrepo/tags/list", auth="jwt", expected_code=200
        )
        data = json.loads(response.text)
        self.assertEqual(data["name"], "devtable/newrepo")
        self.assertIn("latest", data["tags"])
        self.assertIn("foobar", data["tags"])

        # Retrieve the tags with pagination.
        response = self.conduct(
            "GET", "/v2/devtable/newrepo/tags/list", auth="jwt", params=dict(n=1), expected_code=200
        )

        data = json.loads(response.text)
        self.assertEqual(data["name"], "devtable/newrepo")
        self.assertEqual(len(data["tags"]), 1)

        # Try to get tags before a repo exists.
        response = self.conduct(
            "GET", "/v2/devtable/doesnotexist/tags/list", auth="jwt", expected_code=401
        )

        # Assert 401s to non-auth endpoints also get the WWW-Authenticate header.
        self.assertIn("WWW-Authenticate", response.headers)
        self.assertIn(
            'scope="repository:devtable/doesnotexist:pull"', response.headers["WWW-Authenticate"]
        )

    def test_one_five_blacklist(self):
        self.conduct("GET", "/v2/", expected_code=404, user_agent="Go 1.1 package http")

    def test_normal_catalog(self):
        # Look for public repositories and ensure all are public.
        with TestFeature(self, "PUBLIC_CATALOG", False):
            response = self.conduct("GET", "/v2/_catalog")
            data = response.json()
            self.assertTrue(len(data["repositories"]) == 0)

            # Perform auth and lookup the catalog again.
            self.do_auth("devtable", "password", "devtable", "simple")
            all_repos = []

            response = self.conduct("GET", "/v2/_catalog", params=dict(n=2), auth="jwt")
            data = response.json()
            self.assertEqual(len(data["repositories"]), 2)

    def test_public_catalog(self):
        # Look for public repositories and ensure all are public.
        with TestFeature(self, "PUBLIC_CATALOG", True):
            response = self.conduct("GET", "/v2/_catalog")
            data = response.json()
            self.assertTrue(len(data["repositories"]) > 0)

            for reponame in data["repositories"]:
                self.assertTrue(reponame.find("public/") == 0)

            # Perform auth and lookup the catalog again.
            self.do_auth("devtable", "password", "devtable", "simple")
            all_repos = []

            response = self.conduct("GET", "/v2/_catalog", params=dict(n=2), auth="jwt")
            data = response.json()
            self.assertEqual(len(data["repositories"]), 2)
            all_repos.extend(data["repositories"])

            # Ensure we have a next link.
            self.assertIsNotNone(response.headers.get("Link"))

            # Request with the next link.
            while response.headers.get("Link"):
                link_url = response.headers.get("Link")[1:].split(";")[0][:-1]
                v2_index = link_url.find("/v2/")
                relative_url = link_url[v2_index:]

                next_response = self.conduct("GET", relative_url, auth="jwt")
                next_data = next_response.json()
                all_repos.extend(next_data["repositories"])

                self.assertTrue(len(next_data["repositories"]) <= 2)
                self.assertNotEqual(next_data["repositories"], data["repositories"])
                response = next_response

            # Ensure the authed request has the public repository.
            public = [reponame for reponame in all_repos if reponame.find("/publicrepo") >= 0]
            self.assertTrue(bool(public))


class V1PushV2PullRegistryTests(
    V2RegistryPullMixin,
    V1RegistryPushMixin,
    RegistryTestsMixin,
    RegistryTestCaseMixin,
    LiveServerTestCase,
):
    """
    Tests for V1 push, V2 pull registry.
    """

    def test_multiple_tag_with_pull(self):
        """
        Tagging the same exact V1 tag multiple times and then pulling with V2.
        """
        images = self._get_default_images()

        self.do_push("devtable", "newrepo", "devtable", "password", images=images)
        self.do_pull("devtable", "newrepo", "devtable", "password", images=images)

        self.do_tag("devtable", "newrepo", "latest", images[0]["id"], auth=("devtable", "password"))
        self.do_pull("devtable", "newrepo", "devtable", "password", images=images)


class V1PullV2PushRegistryTests(
    V1RegistryPullMixin,
    V2RegistryPushMixin,
    RegistryTestsMixin,
    RegistryTestCaseMixin,
    LiveServerTestCase,
):
    """
    Tests for V1 pull, V2 push registry.
    """


class TorrentTestMixin(V2RegistryPullMixin):
    """
    Mixin of tests for torrent support.
    """

    def get_torrent(self, blobsum):
        # Enable direct download URLs in fake storage.
        self.conduct("POST", "/__test/fakestoragedd/true")

        response = self.conduct(
            "GET", "/c1/torrent/devtable/newrepo/blobs/" + blobsum, auth=("devtable", "password")
        )

        # Disable direct download URLs in fake storage.
        self.conduct("POST", "/__test/fakestoragedd/false")

        return response.content

    def test_get_basic_torrent(self):
        initial_images = [
            {"id": "initialid", "contents": "the initial image",},
        ]

        # Create the repo.
        self.do_push("devtable", "newrepo", "devtable", "password", images=initial_images)

        # Retrieve the manifest for the tag.
        blobs, _ = self.do_pull(
            "devtable",
            "newrepo",
            "devtable",
            "password",
            manifest_id="latest",
            images=initial_images,
        )
        self.assertEqual(1, len(list(blobs.keys())))
        blobsum = list(blobs.keys())[0]

        # Retrieve the torrent for the tag.
        torrent = self.get_torrent(blobsum)
        contents = bencode.bdecode(torrent)

        # Ensure that there is a webseed.
        self.assertEqual(contents["url-list"], "http://somefakeurl?goes=here")

        # Ensure there is an announce and some pieces.
        self.assertIsNotNone(contents.get("info", {}).get("pieces"))
        self.assertIsNotNone(contents.get("announce"))

        sha = resumablehashlib.sha1()
        sha.update(blobs[blobsum])

        expected = binascii.hexlify(sha.digest())
        found = binascii.hexlify(contents["info"]["pieces"])

        self.assertEqual(expected, found)


class TorrentV1PushTests(
    RegistryTestCaseMixin, TorrentTestMixin, V1RegistryPushMixin, LiveServerTestCase
):
    """
    Torrent tests via V1 push.
    """

    pass


class TorrentV2PushTests(
    RegistryTestCaseMixin, TorrentTestMixin, V2RegistryPushMixin, LiveServerTestCase
):
    """
    Torrent tests via V2 push.
    """

    pass


class SquashingTests(RegistryTestCaseMixin, V1RegistryPushMixin, LiveServerTestCase):
    """
    Tests for registry squashing.
    """

    def get_squashed_image(self, auth="sig"):
        response = self.conduct("GET", "/c1/squash/devtable/newrepo/latest", auth=auth)
        tar = tarfile.open(fileobj=StringIO(response.content))
        return tar, response.content

    def test_squashed_with_credentials(self):
        initial_images = [
            {"id": "initialid", "contents": "the initial image",},
        ]

        # Create the repo.
        self.do_push("devtable", "newrepo", "devtable", "password", images=initial_images)
        initial_image_id = "9d35b270436387f821e08de0dfdd501efd70de893ec2c2c7cb01ef19008bee7a"

        # Pull the squashed version of the tag.
        tar, _ = self.get_squashed_image(auth=("devtable", "password"))
        self.assertTrue(initial_image_id in tar.getnames())

    def test_squashed_changes(self):
        initial_images = [
            {"id": "initialid", "contents": "the initial image",},
        ]

        # Create the repo.
        self.do_push("devtable", "newrepo", "devtable", "password", images=initial_images)
        initial_image_id = "9d35b270436387f821e08de0dfdd501efd70de893ec2c2c7cb01ef19008bee7a"

        # Pull the squashed version of the tag.
        tar, _ = self.get_squashed_image()
        self.assertTrue(initial_image_id in tar.getnames())

        # Change the images.
        updated_images = [
            {"id": "updatedid", "contents": "the updated image",},
        ]

        self.do_push("devtable", "newrepo", "devtable", "password", images=updated_images)
        updated_image_id = "f8f5aaffe85708245f5341597a5567b3944f8ba823a1f094e8760fa3e689c9d1"

        # Pull the squashed version of the tag and ensure it has changed.
        tar, _ = self.get_squashed_image()
        self.assertTrue(updated_image_id in tar.getnames())

    def test_estimated_squashing(self):
        initial_images = [
            {"id": "initialid", "contents": "the initial image", "size": 2002,},
        ]

        # Create the repo.
        self.do_push("devtable", "newrepo", "devtable", "password", images=initial_images)

        # NULL out the uncompressed size to force estimation.
        self.conduct("POST", "/__test/removeuncompressed/initialid")

        # Pull the squashed version of the tag.
        initial_image_id = "9d35b270436387f821e08de0dfdd501efd70de893ec2c2c7cb01ef19008bee7a"
        tar, _ = self.get_squashed_image()
        self.assertTrue(initial_image_id in tar.getnames())

    def test_multilayer_squashing(self):
        images = [
            {"id": "baseid", "contents": "The base image",},
            {"id": "latestid", "contents": "the latest image", "parent": "baseid",},
        ]

        # Create the repo.
        self.do_push("devtable", "newrepo", "devtable", "password", images=images)

        # Pull the squashed version of the tag.
        expected_image_id = "9d35b270436387f821e08de0dfdd501efd70de893ec2c2c7cb01ef19008bee7a"

        expected_names = [
            "repositories",
            expected_image_id,
            "%s/json" % expected_image_id,
            "%s/VERSION" % expected_image_id,
            "%s/layer.tar" % expected_image_id,
        ]

        tar, _ = self.get_squashed_image()
        self.assertEqual(expected_names, tar.getnames())
        self.assertEqual(
            "1.0", tar.extractfile(tar.getmember("%s/VERSION" % expected_image_id)).read()
        )

        json_data = tar.extractfile(tar.getmember("%s/json" % expected_image_id)).read()

        # Ensure the JSON loads and parses.
        result = json.loads(json_data)
        self.assertEqual(expected_image_id, result["id"])

        # Ensure that the "image_name" file refers to the latest image, as it is the top layer.
        layer_tar = tarfile.open(
            fileobj=tar.extractfile(tar.getmember("%s/layer.tar" % expected_image_id))
        )
        image_contents = layer_tar.extractfile(layer_tar.getmember("contents")).read()
        self.assertEqual("the latest image", image_contents)

    def test_squashed_torrent(self):
        initial_images = [
            {"id": "initialid", "contents": "the initial image",},
        ]

        # Create the repo.
        self.do_push("devtable", "newrepo", "devtable", "password", images=initial_images)
        initial_image_id = "9d35b270436387f821e08de0dfdd501efd70de893ec2c2c7cb01ef19008bee7a"

        # Try to pull the torrent of the squashed image. This should fail with a 406 since the
        # squashed image doesn't yet exist.
        self.conduct(
            "GET",
            "/c1/squash/devtable/newrepo/latest",
            auth=("devtable", "password"),
            headers=dict(accept="application/x-bittorrent"),
            expected_code=406,
        )

        # Pull the squashed version of the tag.
        tar, squashed = self.get_squashed_image()
        self.assertTrue(initial_image_id in tar.getnames())

        # Enable direct download URLs in fake storage.
        self.conduct("POST", "/__test/fakestoragedd/true")

        # Pull the torrent.
        response = self.conduct(
            "GET",
            "/c1/squash/devtable/newrepo/latest",
            auth=("devtable", "password"),
            headers=dict(accept="application/x-bittorrent"),
        )

        # Disable direct download URLs in fake storage.
        self.conduct("POST", "/__test/fakestoragedd/false")

        # Ensure the torrent is valid.
        contents = bencode.bdecode(response.content)

        # Ensure that there is a webseed.
        self.assertEqual(contents["url-list"], "http://somefakeurl?goes=here")

        # Ensure there is an announce and some pieces.
        self.assertIsNotNone(contents.get("info", {}).get("pieces"))
        self.assertIsNotNone(contents.get("announce"))

        # Ensure the SHA1 matches the generated tar.
        sha = resumablehashlib.sha1()
        sha.update(squashed)

        expected = binascii.hexlify(sha.digest())
        found = binascii.hexlify(contents["info"]["pieces"])

        self.assertEqual(expected, found)


class LoginTests(object):
    """
    Generic tests for registry login.
    """

    def test_invalid_username_knownrepo(self):
        self.do_login(
            "invaliduser",
            "somepassword",
            expect_success=False,
            scope="repository:devtable/simple:pull",
        )

    def test_invalid_password_knownrepo(self):
        self.do_login(
            "devtable",
            "somepassword",
            expect_success=False,
            scope="repository:devtable/simple:pull",
        )

    def test_validuser_knownrepo(self):
        self.do_login(
            "devtable", "password", expect_success=True, scope="repository:devtable/simple:pull"
        )

    def test_validuser_encryptedpass(self):
        # Generate an encrypted password.
        self.conduct_api_login("devtable", "password")
        resp = self.conduct("POST", "/api/v1/user/clientkey", json_data=dict(password="password"))

        encryptedpassword = resp.json()["key"]
        self.do_login(
            "devtable",
            encryptedpassword,
            expect_success=True,
            scope="repository:devtable/simple:pull",
        )

    def test_robotkey(self):
        # Lookup the robot's password.
        self.conduct_api_login("devtable", "password")
        resp = self.conduct("GET", "/api/v1/user/robots/dtrobot")
        robot_token = resp.json()["token"]

        self.do_login(
            "devtable+dtrobot",
            robot_token,
            expect_success=True,
            scope="repository:devtable/complex:pull",
        )


class V1LoginTests(
    V1RegistryLoginMixin, LoginTests, RegistryTestCaseMixin, BaseRegistryMixin, LiveServerTestCase
):
    """
    Tests for V1 login.
    """

    pass  # No additional tests.


class V2LoginTests(
    V2RegistryLoginMixin, LoginTests, RegistryTestCaseMixin, BaseRegistryMixin, LiveServerTestCase
):
    """
    Tests for V2 login.
    """

    def do_logincheck(
        self, username, password, scope, expected_actions=[], expect_success=True, **kwargs
    ):
        # Perform login to get an auth token.
        response = self.do_login(username, password, scope, expect_success=expect_success, **kwargs)
        if not expect_success:
            return

        # Validate the returned token.
        encoded = response.json()["token"]
        header = "Bearer " + encoded

        payload = decode_bearer_header(header, instance_keys, app.config)
        self.assertIsNotNone(payload)

        if scope is None:
            self.assertEqual(0, len(payload["access"]))
        else:
            self.assertEqual(1, len(payload["access"]))
            self.assertEqual(payload["access"][0]["actions"], expected_actions)

    def test_nouser_noscope(self):
        self.do_logincheck("", "", expect_success=False, scope=None)

    def test_validuser_unknownrepo(self):
        self.do_logincheck(
            "devtable",
            "password",
            expect_success=True,
            scope="repository:invalidnamespace/simple:pull",
            expected_actions=[],
        )

    def test_validuser_unknownnamespacerepo(self):
        self.do_logincheck(
            "devtable",
            "password",
            expect_success=True,
            scope="repository:devtable/newrepo:push",
            expected_actions=["push"],
        )

    def test_validuser_noaccess(self):
        self.do_logincheck(
            "public",
            "password",
            expect_success=True,
            scope="repository:devtable/simple:pull",
            expected_actions=[],
        )

    def test_validuser_withendpoint(self):
        self.do_logincheck(
            "devtable",
            "password",
            expect_success=True,
            scope="repository:localhost:5000/devtable/simple:pull,push",
            expected_actions=["push", "pull"],
        )

    def test_validuser_invalid_endpoint(self):
        self.do_logincheck(
            "public",
            "password",
            expect_success=False,
            expected_failure_code=400,
            scope="repository:someotherrepo.com/devtable/simple:pull,push",
            expected_actions=[],
        )

    def test_validuser_malformed_endpoint(self):
        self.do_logincheck(
            "public",
            "password",
            expect_success=False,
            expected_failure_code=400,
            scope="repository:localhost:5000/registryroot/devtable/simple:pull,push",
            expected_actions=[],
        )

    def test_validuser_noscope(self):
        self.do_logincheck("public", "password", expect_success=True, scope=None)

    def test_invaliduser_noscope(self):
        self.do_logincheck("invaliduser", "invalidpass", expect_success=False, scope=None)

    def test_invalidpassword_noscope(self):
        self.do_logincheck("public", "invalidpass", expect_success=False, scope=None)

    def test_nouser_pull_publicrepo(self):
        self.do_logincheck(
            "",
            "",
            expect_success=True,
            scope="repository:public/publicrepo:pull",
            expected_actions=["pull"],
        )

    def test_nouser_push_publicrepo(self):
        self.do_logincheck(
            "",
            "",
            expect_success=True,
            scope="repository:public/publicrepo:push",
            expected_actions=[],
        )

    def test_library_invaliduser(self):
        self.do_logincheck(
            "invaliduser", "password", expect_success=False, scope="repository:librepo:pull,push"
        )

    def test_library_noaccess(self):
        self.do_logincheck(
            "freshuser",
            "password",
            expect_success=True,
            scope="repository:librepo:pull,push",
            expected_actions=[],
        )

    def test_library_access(self):
        self.do_logincheck(
            "devtable",
            "password",
            expect_success=True,
            scope="repository:librepo:pull,push",
            expected_actions=["push", "pull"],
        )

    def test_nouser_pushpull_publicrepo(self):
        # Note: Docker 1.8.3 will ask for both push and pull scopes at all times. For public pulls
        # with no credentials, we were returning a 401. This test makes sure we get back just a pull
        # token.
        self.do_logincheck(
            "",
            "",
            expect_success=True,
            scope="repository:public/publicrepo:pull,push",
            expected_actions=["pull"],
        )


if __name__ == "__main__":
    unittest.main()
