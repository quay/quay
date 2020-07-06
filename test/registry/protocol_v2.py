import hashlib
import json

from enum import Enum, unique

from image.docker.schema1 import (
    DockerSchema1ManifestBuilder,
    DockerSchema1Manifest,
    DOCKER_SCHEMA1_CONTENT_TYPES,
)
from image.docker.schema2 import DOCKER_SCHEMA2_CONTENT_TYPES
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.docker.schema2.config import DockerSchema2Config
from image.oci import OCI_CONTENT_TYPES
from image.oci.manifest import OCIManifestBuilder
from image.oci.config import OCIConfig
from image.shared.schemas import (
    parse_manifest_from_bytes,
    is_manifest_list_type,
    MANIFEST_LIST_TYPES,
)
from test.registry.protocols import (
    RegistryProtocol,
    Failures,
    ProtocolOptions,
    PushResult,
    PullResult,
)
from util.bytes import Bytes


@unique
class V2ProtocolSteps(Enum):
    """
    Defines the various steps of the protocol, for matching failures.
    """

    AUTH = "auth"
    BLOB_HEAD_CHECK = "blob-head-check"
    GET_MANIFEST = "get-manifest"
    GET_MANIFEST_LIST = "get-manifest-list"
    PUT_MANIFEST = "put-manifest"
    PUT_MANIFEST_LIST = "put-manifest-list"
    MOUNT_BLOB = "mount-blob"
    CATALOG = "catalog"
    LIST_TAGS = "list-tags"
    START_UPLOAD = "start-upload"
    GET_BLOB = "get-blob"


class V2Protocol(RegistryProtocol):
    FAILURE_CODES = {
        V2ProtocolSteps.AUTH: {
            Failures.UNAUTHENTICATED: 401,
            Failures.INVALID_AUTHENTICATION: 401,
            Failures.INVALID_REGISTRY: 400,
            Failures.APP_REPOSITORY: 405,
            Failures.ANONYMOUS_NOT_ALLOWED: 401,
            Failures.INVALID_REPOSITORY: 400,
            Failures.SLASH_REPOSITORY: 400,
            Failures.NAMESPACE_DISABLED: 405,
        },
        V2ProtocolSteps.MOUNT_BLOB: {
            Failures.UNAUTHORIZED_FOR_MOUNT: 202,
            Failures.READONLY_REGISTRY: 405,
        },
        V2ProtocolSteps.GET_MANIFEST: {
            Failures.UNKNOWN_TAG: 404,
            Failures.UNAUTHORIZED: 401,
            Failures.DISALLOWED_LIBRARY_NAMESPACE: 400,
            Failures.ANONYMOUS_NOT_ALLOWED: 401,
        },
        V2ProtocolSteps.GET_BLOB: {Failures.GEO_BLOCKED: 403,},
        V2ProtocolSteps.BLOB_HEAD_CHECK: {Failures.DISALLOWED_LIBRARY_NAMESPACE: 400,},
        V2ProtocolSteps.START_UPLOAD: {
            Failures.DISALLOWED_LIBRARY_NAMESPACE: 400,
            Failures.READ_ONLY: 401,
            Failures.MIRROR_ONLY: 401,
            Failures.MIRROR_MISCONFIGURED: 401,
            Failures.MIRROR_ROBOT_MISSING: 401,
            Failures.READ_ONLY: 401,
            Failures.READONLY_REGISTRY: 405,
        },
        V2ProtocolSteps.PUT_MANIFEST: {
            Failures.DISALLOWED_LIBRARY_NAMESPACE: 400,
            Failures.MISSING_TAG: 404,
            Failures.INVALID_TAG: 404,
            Failures.INVALID_IMAGES: 400,
            Failures.INVALID_BLOB: 400,
            Failures.UNSUPPORTED_CONTENT_TYPE: 415,
            Failures.READ_ONLY: 401,
            Failures.MIRROR_ONLY: 401,
            Failures.MIRROR_MISCONFIGURED: 401,
            Failures.MIRROR_ROBOT_MISSING: 401,
            Failures.READONLY_REGISTRY: 405,
            Failures.INVALID_MANIFEST: 400,
        },
        V2ProtocolSteps.PUT_MANIFEST_LIST: {
            Failures.INVALID_MANIFEST_IN_LIST: 400,
            Failures.READ_ONLY: 401,
            Failures.MIRROR_ONLY: 401,
            Failures.MIRROR_MISCONFIGURED: 401,
            Failures.MIRROR_ROBOT_MISSING: 401,
            Failures.READONLY_REGISTRY: 405,
        },
    }

    def __init__(self, jwk, schema="schema1"):
        self.jwk = jwk
        self.schema = schema

    def ping(self, session):
        result = session.get("/v2/")
        assert result.status_code == 401
        assert result.headers["Docker-Distribution-API-Version"] == "registry/2.0"

    def login(self, session, username, password, scopes, expect_success):
        scopes = scopes if isinstance(scopes, list) else [scopes]
        params = {
            "account": username,
            "service": "localhost:5000",
            "scope": scopes,
        }

        auth = (username, password)
        if not username or not password:
            auth = None

        response = session.get("/v2/auth", params=params, auth=auth)
        if expect_success:
            assert response.status_code // 100 == 2
        else:
            assert response.status_code // 100 == 4

        return response

    def auth(self, session, credentials, namespace, repo_name, scopes=None, expected_failure=None):
        """
        Performs the V2 Auth flow, returning the token (if any) and the response.

        Spec: https://docs.docker.com/registry/spec/auth/token/
        """

        scopes = scopes or []
        auth = None
        username = None

        if credentials is not None:
            username, _ = credentials
            auth = credentials

        params = {
            "account": username,
            "service": "localhost:5000",
        }

        if scopes:
            params["scope"] = scopes

        response = self.conduct(
            session,
            "GET",
            "/v2/auth",
            params=params,
            auth=auth,
            expected_status=(200, expected_failure, V2ProtocolSteps.AUTH),
        )
        expect_token = expected_failure is None or not V2Protocol.FAILURE_CODES[
            V2ProtocolSteps.AUTH
        ].get(expected_failure)
        if expect_token:
            assert response.json().get("token") is not None
            return response.json().get("token"), response

        return None, response

    def pull_list(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        manifestlist,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        options = options or ProtocolOptions()
        scopes = options.scopes or [
            "repository:%s:push,pull" % self.repo_name(namespace, repo_name)
        ]
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        token, _ = self.auth(
            session,
            credentials,
            namespace,
            repo_name,
            scopes=scopes,
            expected_failure=expected_failure,
        )
        if token is None:
            assert V2Protocol.FAILURE_CODES[V2ProtocolSteps.AUTH].get(expected_failure)
            return

        headers = {
            "Authorization": "Bearer " + token,
            "Accept": ",".join(MANIFEST_LIST_TYPES),
        }

        for tag_name in tag_names:
            # Retrieve the manifest for the tag or digest.
            response = self.conduct(
                session,
                "GET",
                "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), tag_name),
                expected_status=(200, expected_failure, V2ProtocolSteps.GET_MANIFEST_LIST),
                headers=headers,
            )
            if expected_failure is not None:
                return None

            # Parse the returned manifest list and ensure it matches.
            ct = response.headers["Content-Type"]
            assert is_manifest_list_type(ct), "Expected list type, found: %s" % ct
            retrieved = parse_manifest_from_bytes(Bytes.for_string_or_unicode(response.text), ct)
            assert retrieved.schema_version == 2
            assert retrieved.is_manifest_list
            assert retrieved.digest == manifestlist.digest

            # Pull each of the manifests inside and ensure they can be retrieved.
            for manifest_digest in retrieved.child_manifest_digests():
                response = self.conduct(
                    session,
                    "GET",
                    "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), manifest_digest),
                    expected_status=(200, expected_failure, V2ProtocolSteps.GET_MANIFEST),
                    headers=headers,
                )
                if expected_failure is not None:
                    return None

                ct = response.headers["Content-Type"]
                manifest = parse_manifest_from_bytes(Bytes.for_string_or_unicode(response.text), ct)
                assert not manifest.is_manifest_list
                assert manifest.digest == manifest_digest

    def push_list(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        manifestlist,
        manifests,
        blobs,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        options = options or ProtocolOptions()
        scopes = options.scopes or [
            "repository:%s:push,pull" % self.repo_name(namespace, repo_name)
        ]
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        token, _ = self.auth(
            session,
            credentials,
            namespace,
            repo_name,
            scopes=scopes,
            expected_failure=expected_failure,
        )
        if token is None:
            assert V2Protocol.FAILURE_CODES[V2ProtocolSteps.AUTH].get(expected_failure)
            return

        headers = {
            "Authorization": "Bearer " + token,
            "Accept": ",".join(options.accept_mimetypes)
            if options.accept_mimetypes is not None
            else "*/*",
        }

        # Push all blobs.
        if not self._push_blobs(
            blobs, session, namespace, repo_name, headers, options, expected_failure
        ):
            return

        # Push the individual manifests.
        for manifest in manifests:
            manifest_headers = {"Content-Type": manifest.media_type}
            manifest_headers.update(headers)

            self.conduct(
                session,
                "PUT",
                "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), manifest.digest),
                data=manifest.bytes.as_encoded_str(),
                expected_status=(201, expected_failure, V2ProtocolSteps.PUT_MANIFEST),
                headers=manifest_headers,
            )

        # Push the manifest list.
        for tag_name in tag_names:
            manifest_headers = {"Content-Type": manifestlist.media_type}
            manifest_headers.update(headers)

            if options.manifest_content_type is not None:
                manifest_headers["Content-Type"] = options.manifest_content_type

            self.conduct(
                session,
                "PUT",
                "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), tag_name),
                data=manifestlist.bytes.as_encoded_str(),
                expected_status=(201, expected_failure, V2ProtocolSteps.PUT_MANIFEST_LIST),
                headers=manifest_headers,
            )

        return PushResult(manifests=None, headers=headers)

    def build_oci(self, images, blobs, options):
        builder = OCIManifestBuilder()
        for image in images:
            checksum = "sha256:" + hashlib.sha256(image.bytes).hexdigest()

            if image.urls is None:
                blobs[checksum] = image.bytes

            # If invalid blob references were requested, just make it up.
            if options.manifest_invalid_blob_references:
                checksum = "sha256:" + hashlib.sha256(b"notarealthing").hexdigest()

            if not image.is_empty:
                builder.add_layer(checksum, len(image.bytes), urls=image.urls)

        def history_for_image(image):
            history = {
                "created": "2018-04-03T18:37:09.284840891Z",
                "created_by": (
                    ("/bin/sh -c #(nop) ENTRYPOINT %s" % image.config["Entrypoint"])
                    if image.config and image.config.get("Entrypoint")
                    else "/bin/sh -c #(nop) %s" % image.id
                ),
            }

            if image.is_empty:
                history["empty_layer"] = True

            return history

        config = {
            "os": "linux",
            "architecture": "amd64",
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [history_for_image(image) for image in images],
        }

        if images[-1].config:
            config["config"] = images[-1].config

        config_json = json.dumps(config, ensure_ascii=options.ensure_ascii)
        oci_config = OCIConfig(Bytes.for_string_or_unicode(config_json))
        builder.set_config(oci_config)

        blobs[oci_config.digest] = oci_config.bytes.as_encoded_str()
        return builder.build(ensure_ascii=options.ensure_ascii)

    def build_schema2(self, images, blobs, options):
        builder = DockerSchema2ManifestBuilder()
        for image in images:
            checksum = "sha256:" + hashlib.sha256(image.bytes).hexdigest()

            if image.urls is None:
                blobs[checksum] = image.bytes

            # If invalid blob references were requested, just make it up.
            if options.manifest_invalid_blob_references:
                checksum = "sha256:" + hashlib.sha256(b"notarealthing").hexdigest()

            if not image.is_empty:
                builder.add_layer(checksum, len(image.bytes), urls=image.urls)

        def history_for_image(image):
            history = {
                "created": "2018-04-03T18:37:09.284840891Z",
                "created_by": (
                    ("/bin/sh -c #(nop) ENTRYPOINT %s" % image.config["Entrypoint"])
                    if image.config and image.config.get("Entrypoint")
                    else "/bin/sh -c #(nop) %s" % image.id
                ),
            }

            if image.is_empty:
                history["empty_layer"] = True

            return history

        config = {
            "os": "linux",
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [history_for_image(image) for image in images],
        }

        if options.with_broken_manifest_config:
            # NOTE: We are missing the history entry on purpose.
            config = {
                "os": "linux",
                "rootfs": {"type": "layers", "diff_ids": []},
            }

        if images and images[-1].config:
            config["config"] = images[-1].config

        config_json = json.dumps(config, ensure_ascii=options.ensure_ascii)
        schema2_config = DockerSchema2Config(
            Bytes.for_string_or_unicode(config_json),
            skip_validation_for_testing=options.with_broken_manifest_config,
        )
        builder.set_config(schema2_config)

        blobs[schema2_config.digest] = schema2_config.bytes.as_encoded_str()
        return builder.build(ensure_ascii=options.ensure_ascii)

    def build_schema1(self, namespace, repo_name, tag_name, images, blobs, options, arch="amd64"):
        builder = DockerSchema1ManifestBuilder(namespace, repo_name, tag_name, arch)

        for image in reversed(images):
            assert image.urls is None

            checksum = "sha256:" + hashlib.sha256(image.bytes).hexdigest()
            blobs[checksum] = image.bytes

            # If invalid blob references were requested, just make it up.
            if options.manifest_invalid_blob_references:
                checksum = "sha256:" + hashlib.sha256(b"notarealthing").hexdigest()

            layer_dict = {"id": image.id, "parent": image.parent_id}
            if image.config is not None:
                layer_dict["config"] = image.config

            if image.size is not None:
                layer_dict["Size"] = image.size

            if image.created is not None:
                layer_dict["created"] = image.created

            builder.add_layer(checksum, json.dumps(layer_dict, ensure_ascii=options.ensure_ascii))

        # Build the manifest.
        built = builder.build(self.jwk, ensure_ascii=options.ensure_ascii)

        # Validate it before we send it.
        DockerSchema1Manifest(built.bytes)
        return built

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
        options = options or ProtocolOptions()
        scopes = options.scopes or [
            "repository:%s:push,pull" % self.repo_name(namespace, repo_name)
        ]
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        token, _ = self.auth(
            session,
            credentials,
            namespace,
            repo_name,
            scopes=scopes,
            expected_failure=expected_failure,
        )
        if token is None:
            assert V2Protocol.FAILURE_CODES[V2ProtocolSteps.AUTH].get(expected_failure)
            return

        headers = {
            "Authorization": "Bearer " + token,
            "Accept": ",".join(options.accept_mimetypes)
            if options.accept_mimetypes is not None
            else "*/*",
        }

        # Build fake manifests.
        manifests = {}
        blobs = {}
        for tag_name in tag_names:
            if self.schema == "oci":
                manifests[tag_name] = self.build_oci(images, blobs, options)
            elif self.schema == "schema2":
                manifests[tag_name] = self.build_schema2(images, blobs, options)
            elif self.schema == "schema1":
                manifests[tag_name] = self.build_schema1(
                    namespace, repo_name, tag_name, images, blobs, options
                )
            else:
                raise NotImplementedError(self.schema)

        # Push the blob data.
        if not self._push_blobs(
            blobs, session, namespace, repo_name, headers, options, expected_failure
        ):
            return

        # Write a manifest for each tag.
        for tag_name in tag_names:
            manifest = manifests[tag_name]

            # Write the manifest. If we expect it to be invalid, we expect a 404 code. Otherwise, we
            # expect a 201 response for success.
            put_code = 404 if options.manifest_invalid_blob_references else 201
            manifest_headers = {"Content-Type": manifest.media_type}
            manifest_headers.update(headers)

            if options.manifest_content_type is not None:
                manifest_headers["Content-Type"] = options.manifest_content_type

            tag_or_digest = tag_name if not options.push_by_manifest_digest else manifest.digest
            self.conduct(
                session,
                "PUT",
                "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), tag_or_digest),
                data=manifest.bytes.as_encoded_str(),
                expected_status=(put_code, expected_failure, V2ProtocolSteps.PUT_MANIFEST),
                headers=manifest_headers,
            )

        return PushResult(manifests=manifests, headers=headers)

    def _push_blobs(self, blobs, session, namespace, repo_name, headers, options, expected_failure):
        for blob_digest, blob_bytes in blobs.items():
            if not options.skip_head_checks:
                # Blob data should not yet exist.
                self.conduct(
                    session,
                    "HEAD",
                    "/v2/%s/blobs/%s" % (self.repo_name(namespace, repo_name), blob_digest),
                    expected_status=(404, expected_failure, V2ProtocolSteps.BLOB_HEAD_CHECK),
                    headers=headers,
                )

            # Check for mounting of blobs.
            if options.mount_blobs and blob_digest in options.mount_blobs:
                self.conduct(
                    session,
                    "POST",
                    "/v2/%s/blobs/uploads/" % self.repo_name(namespace, repo_name),
                    params={"mount": blob_digest, "from": options.mount_blobs[blob_digest],},
                    expected_status=(201, expected_failure, V2ProtocolSteps.MOUNT_BLOB),
                    headers=headers,
                )
                if expected_failure is not None:
                    return
            else:
                # Start a new upload of the blob data.
                response = self.conduct(
                    session,
                    "POST",
                    "/v2/%s/blobs/uploads/" % self.repo_name(namespace, repo_name),
                    expected_status=(202, expected_failure, V2ProtocolSteps.START_UPLOAD),
                    headers=headers,
                )
                if response.status_code != 202:
                    continue

                upload_uuid = response.headers["Docker-Upload-UUID"]
                new_upload_location = response.headers["Location"]
                assert new_upload_location.startswith("http://localhost:5000")

                # We need to make this relative just for the tests because the live server test
                # case modifies the port.
                location = response.headers["Location"][len("http://localhost:5000") :]

                # PATCH the data into the blob.
                if options.chunks_for_upload is None:
                    self.conduct(
                        session,
                        "PATCH",
                        location,
                        data=blob_bytes,
                        expected_status=202,
                        headers=headers,
                    )
                else:
                    # If chunked upload is requested, upload the data as a series of chunks, checking
                    # status at every point.
                    for chunk_data in options.chunks_for_upload:
                        if len(chunk_data) == 3:
                            (start_byte, end_byte, expected_code) = chunk_data
                        else:
                            (start_byte, end_byte) = chunk_data
                            expected_code = 202

                        patch_headers = {"Content-Range": "%s-%s" % (start_byte, end_byte)}
                        patch_headers.update(headers)

                        contents_chunk = blob_bytes[start_byte:end_byte]
                        assert len(contents_chunk) == (end_byte - start_byte), "%s vs %s" % (
                            len(contents_chunk),
                            end_byte - start_byte,
                        )
                        self.conduct(
                            session,
                            "PATCH",
                            location,
                            data=contents_chunk,
                            expected_status=expected_code,
                            headers=patch_headers,
                        )
                        if expected_code != 202:
                            return False

                        # Retrieve the upload status at each point, and ensure it is valid.
                        status_url = "/v2/%s/blobs/uploads/%s" % (
                            self.repo_name(namespace, repo_name),
                            upload_uuid,
                        )
                        response = self.conduct(
                            session, "GET", status_url, expected_status=204, headers=headers
                        )
                        assert response.headers["Docker-Upload-UUID"] == upload_uuid
                        assert response.headers["Range"] == "bytes=0-%s" % end_byte, "%s vs %s" % (
                            response.headers["Range"],
                            "bytes=0-%s" % end_byte,
                        )

                if options.cancel_blob_upload:
                    self.conduct(
                        session,
                        "DELETE",
                        location,
                        params=dict(digest=blob_digest),
                        expected_status=204,
                        headers=headers,
                    )

                    # Ensure the upload was canceled.
                    status_url = "/v2/%s/blobs/uploads/%s" % (
                        self.repo_name(namespace, repo_name),
                        upload_uuid,
                    )
                    self.conduct(session, "GET", status_url, expected_status=404, headers=headers)
                    return False

                # Finish the blob upload with a PUT.
                response = self.conduct(
                    session,
                    "PUT",
                    location,
                    params=dict(digest=blob_digest),
                    expected_status=201,
                    headers=headers,
                )
                assert response.headers["Docker-Content-Digest"] == blob_digest

            # Ensure the blob exists now.
            response = self.conduct(
                session,
                "HEAD",
                "/v2/%s/blobs/%s" % (self.repo_name(namespace, repo_name), blob_digest),
                expected_status=200,
                headers=headers,
            )

            assert response.headers["Docker-Content-Digest"] == blob_digest
            assert response.headers["Content-Length"] == str(len(blob_bytes))

            # And retrieve the blob data.
            if not options.skip_blob_push_checks:
                result = self.conduct(
                    session,
                    "GET",
                    "/v2/%s/blobs/%s" % (self.repo_name(namespace, repo_name), blob_digest),
                    headers=headers,
                    expected_status=200,
                )
                assert result.content == blob_bytes

        return True

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
        options = options or ProtocolOptions()
        scopes = options.scopes or ["repository:%s:*" % self.repo_name(namespace, repo_name)]
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        token, _ = self.auth(
            session,
            credentials,
            namespace,
            repo_name,
            scopes=scopes,
            expected_failure=expected_failure,
        )
        if token is None:
            return None

        headers = {
            "Authorization": "Bearer " + token,
        }

        for tag_name in tag_names:
            self.conduct(
                session,
                "DELETE",
                "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), tag_name),
                headers=headers,
                expected_status=202,
            )

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
        scopes = options.scopes or ["repository:%s:pull" % self.repo_name(namespace, repo_name)]
        tag_names = [tag_names] if isinstance(tag_names, str) else tag_names

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        token, _ = self.auth(
            session,
            credentials,
            namespace,
            repo_name,
            scopes=scopes,
            expected_failure=expected_failure,
        )
        if token is None and not options.attempt_pull_without_token:
            return None

        headers = {}
        if token:
            headers = {
                "Authorization": "Bearer " + token,
            }

        if self.schema == "oci":
            headers["Accept"] = ",".join(
                options.accept_mimetypes
                if options.accept_mimetypes is not None
                else OCI_CONTENT_TYPES
            )
        elif self.schema == "schema2":
            headers["Accept"] = ",".join(
                options.accept_mimetypes
                if options.accept_mimetypes is not None
                else DOCKER_SCHEMA2_CONTENT_TYPES
            )

        manifests = {}
        image_ids = {}
        for tag_name in tag_names:
            # Retrieve the manifest for the tag or digest.
            response = self.conduct(
                session,
                "GET",
                "/v2/%s/manifests/%s" % (self.repo_name(namespace, repo_name), tag_name),
                expected_status=(200, expected_failure, V2ProtocolSteps.GET_MANIFEST),
                headers=headers,
            )
            if response.status_code == 401:
                assert "WWW-Authenticate" in response.headers

            response.encoding = "utf-8"
            if expected_failure is not None:
                return None

            # Ensure the manifest returned by us is valid.
            ct = response.headers["Content-Type"]
            if self.schema == "schema1":
                assert ct in DOCKER_SCHEMA1_CONTENT_TYPES

            if options.require_matching_manifest_type:
                if self.schema == "schema1":
                    assert ct in DOCKER_SCHEMA1_CONTENT_TYPES

                if self.schema == "schema2":
                    assert ct in DOCKER_SCHEMA2_CONTENT_TYPES

                if self.schema == "oci":
                    assert ct in OCI_CONTENT_TYPES

            manifest = parse_manifest_from_bytes(Bytes.for_string_or_unicode(response.text), ct)
            manifests[tag_name] = manifest

            if manifest.schema_version == 1:
                image_ids[tag_name] = manifest.leaf_layer_v1_image_id

            # Verify the blobs.
            layer_index = 0
            empty_count = 0
            blob_digests = list(manifest.blob_digests)
            for image in images:
                if manifest.schema_version == 2 and image.is_empty:
                    empty_count += 1
                    continue

                # If the layer is remote, then we expect the blob to *not* exist in the system.
                blob_digest = blob_digests[layer_index]
                expected_status = 404 if image.urls else 200
                result = self.conduct(
                    session,
                    "GET",
                    "/v2/%s/blobs/%s" % (self.repo_name(namespace, repo_name), blob_digest),
                    expected_status=(expected_status, expected_failure, V2ProtocolSteps.GET_BLOB),
                    headers=headers,
                    options=options,
                )

                if expected_status == 200:
                    assert result.content == image.bytes

                layer_index += 1

            assert (len(blob_digests) + empty_count) >= len(
                images
            )  # OCI/Schema 2 has 1 extra for config

        return PullResult(manifests=manifests, image_ids=image_ids)

    def tags(
        self,
        session,
        namespace,
        repo_name,
        page_size=2,
        credentials=None,
        options=None,
        expected_failure=None,
    ):
        options = options or ProtocolOptions()
        scopes = options.scopes or ["repository:%s:pull" % self.repo_name(namespace, repo_name)]

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        headers = {}
        if credentials is not None:
            token, _ = self.auth(
                session,
                credentials,
                namespace,
                repo_name,
                scopes=scopes,
                expected_failure=expected_failure,
            )
            if token is None:
                return None

            headers = {
                "Authorization": "Bearer " + token,
            }

        results = []
        url = "/v2/%s/tags/list" % (self.repo_name(namespace, repo_name))
        params = {}
        if page_size is not None:
            params["n"] = page_size

        while True:
            response = self.conduct(
                session,
                "GET",
                url,
                headers=headers,
                params=params,
                expected_status=(200, expected_failure, V2ProtocolSteps.LIST_TAGS),
            )
            data = response.json()

            assert len(data["tags"]) <= page_size
            results.extend(data["tags"])

            if not response.headers.get("Link"):
                return results

            link_url = response.headers["Link"]
            v2_index = link_url.find("/v2/")
            url = link_url[v2_index:]

        return results

    def catalog(
        self,
        session,
        page_size=2,
        credentials=None,
        options=None,
        expected_failure=None,
        namespace=None,
        repo_name=None,
        bearer_token=None,
    ):
        options = options or ProtocolOptions()
        scopes = options.scopes or []

        # Ping!
        self.ping(session)

        # Perform auth and retrieve a token.
        headers = {}
        if credentials is not None:
            token, _ = self.auth(
                session,
                credentials,
                namespace,
                repo_name,
                scopes=scopes,
                expected_failure=expected_failure,
            )
            if token is None:
                return None

            headers = {
                "Authorization": "Bearer " + token,
            }

        if bearer_token is not None:
            headers = {
                "Authorization": "Bearer " + bearer_token,
            }

        results = []
        url = "/v2/_catalog"
        params = {}
        if page_size is not None:
            params["n"] = page_size

        while True:
            response = self.conduct(
                session,
                "GET",
                url,
                headers=headers,
                params=params,
                expected_status=(200, expected_failure, V2ProtocolSteps.CATALOG),
            )
            data = response.json()

            assert len(data["repositories"]) <= page_size
            results.extend(data["repositories"])

            if not response.headers.get("Link"):
                return results

            link_url = response.headers["Link"]
            v2_index = link_url.find("/v2/")
            url = link_url[v2_index:]

        return results
