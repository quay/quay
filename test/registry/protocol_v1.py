import json

from io import BytesIO
from enum import Enum, unique

from digest.checksums import compute_simple, compute_tarsum
from test.registry.protocols import (
    RegistryProtocol,
    Failures,
    ProtocolOptions,
    PushResult,
    PullResult,
)


@unique
class V1ProtocolSteps(Enum):
    """
    Defines the various steps of the protocol, for matching failures.
    """

    PUT_IMAGES = "put-images"
    GET_IMAGES = "get-images"
    PUT_TAG = "put-tag"
    PUT_IMAGE_JSON = "put-image-json"
    DELETE_TAG = "delete-tag"
    GET_TAG = "get-tag"
    GET_LAYER = "get-layer"


class V1Protocol(RegistryProtocol):
    FAILURE_CODES = {
        V1ProtocolSteps.PUT_IMAGES: {
            Failures.INVALID_AUTHENTICATION: 403,
            Failures.UNAUTHENTICATED: 401,
            Failures.UNAUTHORIZED: 403,
            Failures.APP_REPOSITORY: 405,
            Failures.SLASH_REPOSITORY: 404,
            Failures.INVALID_REPOSITORY: 400,
            Failures.DISALLOWED_LIBRARY_NAMESPACE: 400,
            Failures.NAMESPACE_DISABLED: 400,
            Failures.READ_ONLY: 405,
            Failures.MIRROR_ONLY: 405,
            Failures.MIRROR_MISCONFIGURED: 500,
            Failures.MIRROR_ROBOT_MISSING: 400,
            Failures.READONLY_REGISTRY: 405,
        },
        V1ProtocolSteps.GET_IMAGES: {
            Failures.INVALID_AUTHENTICATION: 403,
            Failures.UNAUTHENTICATED: 403,
            Failures.UNAUTHORIZED: 403,
            Failures.APP_REPOSITORY: 404,
            Failures.ANONYMOUS_NOT_ALLOWED: 401,
            Failures.DISALLOWED_LIBRARY_NAMESPACE: 400,
            Failures.NAMESPACE_DISABLED: 400,
        },
        V1ProtocolSteps.PUT_IMAGE_JSON: {
            Failures.INVALID_IMAGES: 400,
            Failures.READ_ONLY: 405,
            Failures.MIRROR_ONLY: 405,
            Failures.MIRROR_MISCONFIGURED: 500,
            Failures.MIRROR_ROBOT_MISSING: 400,
            Failures.READONLY_REGISTRY: 405,
        },
        V1ProtocolSteps.PUT_TAG: {
            Failures.MISSING_TAG: 404,
            Failures.INVALID_TAG: 400,
            Failures.INVALID_IMAGES: 400,
            Failures.NAMESPACE_DISABLED: 400,
            Failures.READ_ONLY: 405,
            Failures.MIRROR_ONLY: 405,
            Failures.MIRROR_MISCONFIGURED: 500,
            Failures.MIRROR_ROBOT_MISSING: 400,
            Failures.READONLY_REGISTRY: 405,
        },
        V1ProtocolSteps.GET_LAYER: {Failures.GEO_BLOCKED: 403,},
        V1ProtocolSteps.GET_TAG: {Failures.UNKNOWN_TAG: 404,},
    }

    def __init__(self, jwk):
        pass

    def _auth_for_credentials(self, credentials):
        if credentials is None:
            return None

        return credentials

    def ping(self, session):
        assert session.get("/v1/_ping").status_code == 200

    def login(self, session, username, password, scopes, expect_success):
        data = {
            "username": username,
            "password": password,
        }

        response = self.conduct(session, "POST", "/v1/users/", json_data=data, expected_status=400)
        assert (response.text == '"Username or email already exists"') == expect_success

    def pull(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        images,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        options = options or ProtocolOptions()
        auth = self._auth_for_credentials(credentials)
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names
        prefix = "/v1/repositories/%s/" % self.repo_name(namespace, repo_name)

        # Ping!
        self.ping(session)

        # GET /v1/repositories/{namespace}/{repository}/images
        headers = {"X-Docker-Token": "true"}
        result = self.conduct(
            session,
            "GET",
            prefix + "images",
            auth=auth,
            headers=headers,
            expected_status=(200, expected_failure, V1ProtocolSteps.GET_IMAGES),
        )
        if result.status_code != 200:
            return

        headers = {}
        if credentials is not None:
            headers["Authorization"] = "token " + result.headers["www-authenticate"]
        else:
            assert not "www-authenticate" in result.headers

        # GET /v1/repositories/{namespace}/{repository}/tags
        image_ids = self.conduct(session, "GET", prefix + "tags", headers=headers).json()

        for tag_name in tag_names:
            # GET /v1/repositories/{namespace}/{repository}/tags/<tag_name>
            image_id_data = self.conduct(
                session,
                "GET",
                prefix + "tags/" + tag_name,
                headers=headers,
                expected_status=(200, expected_failure, V1ProtocolSteps.GET_TAG),
            )

            if tag_name not in image_ids:
                assert expected_failure == Failures.UNKNOWN_TAG
                return None

            if expected_failure == Failures.UNKNOWN_TAG:
                return None

            tag_image_id = image_ids[tag_name]
            assert image_id_data.json() == tag_image_id

            # Retrieve the ancestry of the tagged image.
            image_prefix = "/v1/images/%s/" % tag_image_id
            ancestors = self.conduct(
                session, "GET", image_prefix + "ancestry", headers=headers
            ).json()

            assert len(ancestors) == len(images)
            for index, image_id in enumerate(reversed(ancestors)):
                # /v1/images/{imageID}/{ancestry, json, layer}
                image_prefix = "/v1/images/%s/" % image_id
                self.conduct(session, "GET", image_prefix + "ancestry", headers=headers)

                result = self.conduct(session, "GET", image_prefix + "json", headers=headers)
                assert result.json()["id"] == image_id

                # Ensure we can HEAD the image layer.
                self.conduct(session, "HEAD", image_prefix + "layer", headers=headers)

                # And retrieve the layer data.
                result = self.conduct(
                    session,
                    "GET",
                    image_prefix + "layer",
                    headers=headers,
                    expected_status=(200, expected_failure, V1ProtocolSteps.GET_LAYER),
                    options=options,
                )
                if result.status_code == 200:
                    assert result.content == images[index].bytes

        return PullResult(manifests=None, image_ids=image_ids)

    def push(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        images,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        auth = self._auth_for_credentials(credentials)
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        # PUT /v1/repositories/{namespace}/{repository}/
        result = self.conduct(
            session,
            "PUT",
            "/v1/repositories/%s/" % self.repo_name(namespace, repo_name),
            expected_status=(201, expected_failure, V1ProtocolSteps.PUT_IMAGES),
            json_data={},
            auth=auth,
        )
        if result.status_code != 201:
            return

        headers = {}
        headers["Authorization"] = "token " + result.headers["www-authenticate"]

        for image in images:
            assert image.urls is None

            # PUT /v1/images/{imageID}/json
            image_json_data = {"id": image.id}
            if image.size is not None:
                image_json_data["Size"] = image.size

            if image.parent_id is not None:
                image_json_data["parent"] = image.parent_id

            if image.config is not None:
                image_json_data["config"] = image.config

            if image.created is not None:
                image_json_data["created"] = image.created

            image_json = json.dumps(image_json_data)

            response = self.conduct(
                session,
                "PUT",
                "/v1/images/%s/json" % image.id,
                data=image_json,
                headers=headers,
                expected_status=(200, expected_failure, V1ProtocolSteps.PUT_IMAGE_JSON),
            )
            if response.status_code != 200:
                return

            # PUT /v1/images/{imageID}/checksum (old style)
            old_checksum = compute_tarsum(BytesIO(image.bytes), image_json)
            checksum_headers = {"X-Docker-Checksum": old_checksum}
            checksum_headers.update(headers)

            self.conduct(
                session, "PUT", "/v1/images/%s/checksum" % image.id, headers=checksum_headers
            )

            # PUT /v1/images/{imageID}/layer
            self.conduct(
                session,
                "PUT",
                "/v1/images/%s/layer" % image.id,
                data=BytesIO(image.bytes),
                headers=headers,
            )

            # PUT /v1/images/{imageID}/checksum (new style)
            checksum = compute_simple(BytesIO(image.bytes), image_json)
            checksum_headers = {"X-Docker-Checksum-Payload": checksum}
            checksum_headers.update(headers)

            self.conduct(
                session, "PUT", "/v1/images/%s/checksum" % image.id, headers=checksum_headers
            )

        # PUT /v1/repositories/{namespace}/{repository}/tags/latest
        for tag_name in tag_names:
            self.conduct(
                session,
                "PUT",
                "/v1/repositories/%s/tags/%s" % (self.repo_name(namespace, repo_name), tag_name),
                data='"%s"' % images[-1].id,
                headers=headers,
                expected_status=(200, expected_failure, V1ProtocolSteps.PUT_TAG),
            )

        # PUT /v1/repositories/{namespace}/{repository}/images
        self.conduct(
            session,
            "PUT",
            "/v1/repositories/%s/images" % self.repo_name(namespace, repo_name),
            expected_status=204,
            headers=headers,
        )

        return PushResult(manifests=None, headers=headers)

    def delete(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        auth = self._auth_for_credentials(credentials)
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        for tag_name in tag_names:
            # DELETE /v1/repositories/{namespace}/{repository}/tags/{tag}
            self.conduct(
                session,
                "DELETE",
                "/v1/repositories/%s/tags/%s" % (self.repo_name(namespace, repo_name), tag_name),
                auth=auth,
                expected_status=(200, expected_failure, V1ProtocolSteps.DELETE_TAG),
            )

    def tag(
        self,
        session,
        namespace,
        repo_name,
        tag_name,
        image_id,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        auth = self._auth_for_credentials(credentials)
        self.conduct(
            session,
            "PUT",
            "/v1/repositories/%s/tags/%s" % (self.repo_name(namespace, repo_name), tag_name),
            data='"%s"' % image_id,
            auth=auth,
            expected_status=(200, expected_failure, V1ProtocolSteps.PUT_TAG),
        )
