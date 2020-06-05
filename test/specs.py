import json
import hashlib

from flask import url_for
from base64 import b64encode


NO_REPO = None
PUBLIC = "public"
PUBLIC_REPO_NAME = "publicrepo"
PUBLIC_REPO = PUBLIC + "/" + PUBLIC_REPO_NAME

PRIVATE = "devtable"
PRIVATE_REPO_NAME = "shared"
PRIVATE_REPO = PRIVATE + "/" + PRIVATE_REPO_NAME

ORG = "buynlarge"
ORG_REPO = ORG + "/orgrepo"
ANOTHER_ORG_REPO = ORG + "/anotherorgrepo"
NEW_ORG_REPO = ORG + "/neworgrepo"

ORG_REPO_NAME = "orgrepo"
ORG_READERS = "readers"
ORG_OWNER = "devtable"
ORG_OWNERS = "owners"
ORG_READERS = "readers"

FAKE_MANIFEST = "unknown_tag"
FAKE_DIGEST = "sha256:" + hashlib.sha256(b"fake").hexdigest()
FAKE_IMAGE_ID = "fake-image"
FAKE_UPLOAD_ID = "fake-upload"
FAKE_TAG_NAME = "fake-tag"
FAKE_USERNAME = "fakeuser"
FAKE_TOKEN = "fake-token"
FAKE_WEBHOOK = "fake-webhook"

BUILD_UUID = "123"
TRIGGER_UUID = "123"

NEW_ORG_REPO_DETAILS = {
    "repository": "fake-repository",
    "visibility": "private",
    "description": "",
    "namespace": ORG,
}

NEW_USER_DETAILS = {
    "username": "bobby",
    "password": "password",
    "email": "bobby@tables.com",
}

SEND_RECOVERY_DETAILS = {
    "email": "jacob.moshenko@gmail.com",
}

SIGNIN_DETAILS = {
    "username": "devtable",
    "password": "password",
}

FILE_DROP_DETAILS = {
    "mimeType": "application/zip",
}

CHANGE_PERMISSION_DETAILS = {
    "role": "admin",
}

CREATE_BUILD_DETAILS = {
    "file_id": "fake-file-id",
}

CHANGE_VISIBILITY_DETAILS = {
    "visibility": "public",
}

CREATE_TOKEN_DETAILS = {
    "friendlyName": "A new token",
}

UPDATE_REPO_DETAILS = {
    "description": "A new description",
}


class IndexV1TestSpec(object):
    def __init__(
        self,
        url,
        sess_repo=None,
        anon_code=403,
        no_access_code=403,
        read_code=200,
        creator_code=200,
        admin_code=200,
    ):
        self._url = url
        self._method = "GET"
        self._data = None

        self.sess_repo = sess_repo

        self.anon_code = anon_code
        self.no_access_code = no_access_code
        self.read_code = read_code
        self.creator_code = creator_code
        self.admin_code = admin_code

    def gen_basic_auth(self, username, password):
        encoded = b64encode(b"%s:%s" % (username.encode("ascii"), password.encode("ascii")))
        return "basic %s" % encoded.decode("ascii")

    def set_data_from_obj(self, json_serializable):
        self._data = json.dumps(json_serializable)
        return self

    def set_method(self, method):
        self._method = method
        return self

    def get_client_args(self):
        kwargs = {"method": self._method}

        if self._data or self._method == "POST" or self._method == "PUT" or self._method == "PATCH":
            kwargs["data"] = self._data if self._data else "{}"
            kwargs["content_type"] = "application/json"

        return self._url, kwargs


def build_v1_index_specs():
    return [
        IndexV1TestSpec(
            url_for("v1.get_image_layer", image_id=FAKE_IMAGE_ID),
            PUBLIC_REPO,
            404,
            404,
            404,
            404,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_layer", image_id=FAKE_IMAGE_ID),
            PRIVATE_REPO,
            403,
            403,
            404,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_layer", image_id=FAKE_IMAGE_ID), ORG_REPO, 403, 403, 404, 403, 404
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_layer", image_id=FAKE_IMAGE_ID),
            ANOTHER_ORG_REPO,
            403,
            403,
            403,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.put_image_layer", image_id=FAKE_IMAGE_ID),
            PUBLIC_REPO,
            403,
            403,
            403,
            403,
            403,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_layer", image_id=FAKE_IMAGE_ID),
            PRIVATE_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_layer", image_id=FAKE_IMAGE_ID), ORG_REPO, 403, 403, 403, 403, 400
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_layer", image_id=FAKE_IMAGE_ID),
            ANOTHER_ORG_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_checksum", image_id=FAKE_IMAGE_ID),
            PUBLIC_REPO,
            403,
            403,
            403,
            403,
            403,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_checksum", image_id=FAKE_IMAGE_ID),
            PRIVATE_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_checksum", image_id=FAKE_IMAGE_ID),
            ORG_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_checksum", image_id=FAKE_IMAGE_ID),
            ANOTHER_ORG_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.get_image_json", image_id=FAKE_IMAGE_ID),
            PUBLIC_REPO,
            404,
            404,
            404,
            404,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_json", image_id=FAKE_IMAGE_ID),
            PRIVATE_REPO,
            403,
            403,
            404,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_json", image_id=FAKE_IMAGE_ID), ORG_REPO, 403, 403, 404, 403, 404
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_json", image_id=FAKE_IMAGE_ID),
            ANOTHER_ORG_REPO,
            403,
            403,
            403,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_ancestry", image_id=FAKE_IMAGE_ID),
            PUBLIC_REPO,
            404,
            404,
            404,
            404,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_ancestry", image_id=FAKE_IMAGE_ID),
            PRIVATE_REPO,
            403,
            403,
            404,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_ancestry", image_id=FAKE_IMAGE_ID),
            ORG_REPO,
            403,
            403,
            404,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_image_ancestry", image_id=FAKE_IMAGE_ID),
            ANOTHER_ORG_REPO,
            403,
            403,
            403,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.put_image_json", image_id=FAKE_IMAGE_ID),
            PUBLIC_REPO,
            403,
            403,
            403,
            403,
            403,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_json", image_id=FAKE_IMAGE_ID),
            PRIVATE_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_json", image_id=FAKE_IMAGE_ID), ORG_REPO, 403, 403, 403, 403, 400
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_image_json", image_id=FAKE_IMAGE_ID),
            ANOTHER_ORG_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(url_for("v1.create_user"), NO_REPO, 400, 400, 400, 400, 400)
        .set_method("POST")
        .set_data_from_obj(NEW_USER_DETAILS),
        IndexV1TestSpec(url_for("v1.get_user"), NO_REPO, 404, 200, 200, 200, 200),
        IndexV1TestSpec(
            url_for("v1.update_user", username=FAKE_USERNAME), NO_REPO, 403, 403, 403, 403, 403
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.create_repository", repository=PUBLIC_REPO),
            NO_REPO,
            403,
            403,
            403,
            403,
            403,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.create_repository", repository=PRIVATE_REPO),
            NO_REPO,
            403,
            403,
            403,
            403,
            201,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.create_repository", repository=ORG_REPO), NO_REPO, 403, 403, 403, 403, 201
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.create_repository", repository=ANOTHER_ORG_REPO),
            NO_REPO,
            403,
            403,
            403,
            403,
            201,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.create_repository", repository=NEW_ORG_REPO),
            NO_REPO,
            401,
            403,
            403,
            201,
            201,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.update_images", repository=PUBLIC_REPO), NO_REPO, 403, 403, 403, 403, 403
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.update_images", repository=PRIVATE_REPO), NO_REPO, 403, 403, 403, 403, 400
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.update_images", repository=ORG_REPO), NO_REPO, 403, 403, 403, 403, 400
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.update_images", repository=ANOTHER_ORG_REPO),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.get_repository_images", repository=PUBLIC_REPO),
            NO_REPO,
            200,
            200,
            200,
            200,
            200,
        ),
        IndexV1TestSpec(
            url_for("v1.get_repository_images", repository=PRIVATE_REPO),
            NO_REPO,
            403,
            403,
            200,
            403,
            200,
        ),
        IndexV1TestSpec(
            url_for("v1.get_repository_images", repository=ORG_REPO),
            NO_REPO,
            403,
            403,
            200,
            403,
            200,
        ),
        IndexV1TestSpec(
            url_for("v1.get_repository_images", repository=ANOTHER_ORG_REPO),
            NO_REPO,
            403,
            403,
            403,
            403,
            200,
        ),
        IndexV1TestSpec(
            url_for("v1.delete_repository_images", repository=PUBLIC_REPO),
            NO_REPO,
            501,
            501,
            501,
            501,
            501,
        ).set_method("DELETE"),
        IndexV1TestSpec(
            url_for("v1.put_repository_auth", repository=PUBLIC_REPO),
            NO_REPO,
            501,
            501,
            501,
            501,
            501,
        ).set_method("PUT"),
        IndexV1TestSpec(url_for("v1.get_search"), NO_REPO, 200, 200, 200, 200, 200),
        IndexV1TestSpec(url_for("v1.ping"), NO_REPO, 200, 200, 200, 200, 200),
        IndexV1TestSpec(
            url_for("v1.get_tags", repository=PUBLIC_REPO), NO_REPO, 200, 200, 200, 200, 200
        ),
        IndexV1TestSpec(
            url_for("v1.get_tags", repository=PRIVATE_REPO), NO_REPO, 403, 403, 200, 403, 200
        ),
        IndexV1TestSpec(
            url_for("v1.get_tags", repository=ORG_REPO), NO_REPO, 403, 403, 200, 403, 200
        ),
        IndexV1TestSpec(
            url_for("v1.get_tags", repository=ANOTHER_ORG_REPO), NO_REPO, 403, 403, 403, 403, 200
        ),
        IndexV1TestSpec(
            url_for("v1.get_tag", repository=PUBLIC_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            404,
            404,
            404,
            404,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_tag", repository=PRIVATE_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            404,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_tag", repository=ORG_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            404,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.get_tag", repository=ANOTHER_ORG_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            404,
        ),
        IndexV1TestSpec(
            url_for("v1.put_tag", repository=PUBLIC_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            403,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_tag", repository=PRIVATE_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_tag", repository=ORG_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.put_tag", repository=ANOTHER_ORG_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("PUT"),
        IndexV1TestSpec(
            url_for("v1.delete_tag", repository=PUBLIC_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            403,
        ).set_method("DELETE"),
        IndexV1TestSpec(
            url_for("v1.delete_tag", repository=PRIVATE_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("DELETE"),
        IndexV1TestSpec(
            url_for("v1.delete_tag", repository=ORG_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("DELETE"),
        IndexV1TestSpec(
            url_for("v1.delete_tag", repository=ANOTHER_ORG_REPO, tag=FAKE_TAG_NAME),
            NO_REPO,
            403,
            403,
            403,
            403,
            400,
        ).set_method("DELETE"),
    ]


class IndexV2TestSpec(object):
    def __init__(self, index_name, method_name, repo_name, scope=None, **kwargs):
        self.index_name = index_name
        self.repo_name = repo_name
        self.method_name = method_name

        default_scope = "push,pull" if method_name != "GET" and method_name != "HEAD" else "pull"
        self.scope = scope or default_scope

        self.kwargs = kwargs

        self.anon_code = 401
        self.no_access_code = 403
        self.read_code = 200
        self.admin_code = 200
        self.creator_code = 200

    def request_status(
        self, anon_code=401, no_access_code=403, read_code=200, creator_code=200, admin_code=200
    ):
        self.anon_code = anon_code
        self.no_access_code = no_access_code
        self.read_code = read_code
        self.creator_code = creator_code
        self.admin_code = admin_code
        return self

    def get_url(self):
        return url_for(self.index_name, repository=self.repo_name, **self.kwargs)

    def gen_basic_auth(self, username, password):
        encoded = b64encode(b"%s:%s" % (username.encode("ascii"), password.encode("ascii")))
        return "basic %s" % encoded.decode("ascii")

    def get_scope_string(self):
        return "repository:%s:%s" % (self.repo_name, self.scope)


def build_v2_index_specs():
    return [
        # v2.list_all_tags
        IndexV2TestSpec("v2.list_all_tags", "GET", PUBLIC_REPO).request_status(
            200, 200, 200, 200, 200
        ),
        IndexV2TestSpec("v2.list_all_tags", "GET", PRIVATE_REPO).request_status(
            401, 401, 200, 401, 200
        ),
        IndexV2TestSpec("v2.list_all_tags", "GET", ORG_REPO).request_status(
            401, 401, 200, 401, 200
        ),
        IndexV2TestSpec("v2.list_all_tags", "GET", ANOTHER_ORG_REPO).request_status(
            401, 401, 401, 401, 200
        ),
        # v2.fetch_manifest_by_tagname
        IndexV2TestSpec(
            "v2.fetch_manifest_by_tagname", "GET", PUBLIC_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(404, 404, 404, 404, 404),
        IndexV2TestSpec(
            "v2.fetch_manifest_by_tagname", "GET", PRIVATE_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 404, 401, 404),
        IndexV2TestSpec(
            "v2.fetch_manifest_by_tagname", "GET", ORG_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 404, 401, 404),
        IndexV2TestSpec(
            "v2.fetch_manifest_by_tagname", "GET", ANOTHER_ORG_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 401, 401, 404),
        # v2.fetch_manifest_by_digest
        IndexV2TestSpec(
            "v2.fetch_manifest_by_digest", "GET", PUBLIC_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(404, 404, 404, 404, 404),
        IndexV2TestSpec(
            "v2.fetch_manifest_by_digest", "GET", PRIVATE_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 404, 401, 404),
        IndexV2TestSpec(
            "v2.fetch_manifest_by_digest", "GET", ORG_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 404, 401, 404),
        IndexV2TestSpec(
            "v2.fetch_manifest_by_digest", "GET", ANOTHER_ORG_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 404),
        # v2.write_manifest_by_tagname
        IndexV2TestSpec(
            "v2.write_manifest_by_tagname", "PUT", PUBLIC_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.write_manifest_by_tagname", "PUT", PRIVATE_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 401, 401, 400),
        IndexV2TestSpec(
            "v2.write_manifest_by_tagname", "PUT", ORG_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 401, 401, 400),
        IndexV2TestSpec(
            "v2.write_manifest_by_tagname", "PUT", ANOTHER_ORG_REPO, manifest_ref=FAKE_MANIFEST
        ).request_status(401, 401, 401, 401, 400),
        # v2.write_manifest_by_digest
        IndexV2TestSpec(
            "v2.write_manifest_by_digest", "PUT", PUBLIC_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.write_manifest_by_digest", "PUT", PRIVATE_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 400),
        IndexV2TestSpec(
            "v2.write_manifest_by_digest", "PUT", ORG_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 400),
        IndexV2TestSpec(
            "v2.write_manifest_by_digest", "PUT", ANOTHER_ORG_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 400),
        # v2.delete_manifest_by_digest
        IndexV2TestSpec(
            "v2.delete_manifest_by_digest", "DELETE", PUBLIC_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.delete_manifest_by_digest", "DELETE", PRIVATE_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.delete_manifest_by_digest", "DELETE", ORG_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.delete_manifest_by_digest", "DELETE", ANOTHER_ORG_REPO, manifest_ref=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 404),
        # v2.check_blob_exists
        IndexV2TestSpec(
            "v2.check_blob_exists", "HEAD", PUBLIC_REPO, digest=FAKE_DIGEST
        ).request_status(404, 404, 404, 404, 404),
        IndexV2TestSpec(
            "v2.check_blob_exists", "HEAD", PRIVATE_REPO, digest=FAKE_DIGEST
        ).request_status(401, 401, 404, 401, 404),
        IndexV2TestSpec(
            "v2.check_blob_exists", "HEAD", ORG_REPO, digest=FAKE_DIGEST
        ).request_status(401, 401, 404, 401, 404),
        IndexV2TestSpec(
            "v2.check_blob_exists", "HEAD", ANOTHER_ORG_REPO, digest=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 404),
        # v2.download_blob
        IndexV2TestSpec("v2.download_blob", "GET", PUBLIC_REPO, digest=FAKE_DIGEST).request_status(
            404, 404, 404, 404, 404
        ),
        IndexV2TestSpec("v2.download_blob", "GET", PRIVATE_REPO, digest=FAKE_DIGEST).request_status(
            401, 401, 404, 401, 404
        ),
        IndexV2TestSpec("v2.download_blob", "GET", ORG_REPO, digest=FAKE_DIGEST).request_status(
            401, 401, 404, 401, 404
        ),
        IndexV2TestSpec(
            "v2.download_blob", "GET", ANOTHER_ORG_REPO, digest=FAKE_DIGEST
        ).request_status(401, 401, 401, 401, 404),
        # v2.start_blob_upload
        IndexV2TestSpec("v2.start_blob_upload", "POST", PUBLIC_REPO).request_status(
            401, 401, 401, 401, 401
        ),
        IndexV2TestSpec("v2.start_blob_upload", "POST", PRIVATE_REPO).request_status(
            401, 401, 401, 401, 202
        ),
        IndexV2TestSpec("v2.start_blob_upload", "POST", ORG_REPO).request_status(
            401, 401, 401, 401, 202
        ),
        IndexV2TestSpec("v2.start_blob_upload", "POST", ANOTHER_ORG_REPO).request_status(
            401, 401, 401, 401, 202
        ),
        # v2.fetch_existing_upload
        IndexV2TestSpec(
            "v2.fetch_existing_upload", "GET", PUBLIC_REPO, "push,pull", upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.fetch_existing_upload", "GET", PRIVATE_REPO, "push,pull", upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.fetch_existing_upload", "GET", ORG_REPO, "push,pull", upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.fetch_existing_upload",
            "GET",
            ANOTHER_ORG_REPO,
            "push,pull",
            upload_uuid=FAKE_UPLOAD_ID,
        ).request_status(401, 401, 401, 401, 404),
        # v2.upload_chunk
        IndexV2TestSpec(
            "v2.upload_chunk", "PATCH", PUBLIC_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.upload_chunk", "PATCH", PRIVATE_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.upload_chunk", "PATCH", ORG_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.upload_chunk", "PATCH", ANOTHER_ORG_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        # v2.monolithic_upload_or_last_chunk
        IndexV2TestSpec(
            "v2.monolithic_upload_or_last_chunk", "PUT", PUBLIC_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.monolithic_upload_or_last_chunk", "PUT", PRIVATE_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 400),
        IndexV2TestSpec(
            "v2.monolithic_upload_or_last_chunk", "PUT", ORG_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 400),
        IndexV2TestSpec(
            "v2.monolithic_upload_or_last_chunk",
            "PUT",
            ANOTHER_ORG_REPO,
            upload_uuid=FAKE_UPLOAD_ID,
        ).request_status(401, 401, 401, 401, 400),
        # v2.cancel_upload
        IndexV2TestSpec(
            "v2.cancel_upload", "DELETE", PUBLIC_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 401),
        IndexV2TestSpec(
            "v2.cancel_upload", "DELETE", PRIVATE_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.cancel_upload", "DELETE", ORG_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
        IndexV2TestSpec(
            "v2.cancel_upload", "DELETE", ANOTHER_ORG_REPO, upload_uuid=FAKE_UPLOAD_ID
        ).request_status(401, 401, 401, 401, 404),
    ]
