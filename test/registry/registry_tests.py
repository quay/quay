# pylint: disable=W0401, W0621, W0613, W0614, R0913
import hashlib
import tarfile

from io import BytesIO

import binascii
import bencode
import rehash

from werkzeug.datastructures import Accept

from test.fixtures import *
from test.registry.liveserverfixture import *
from test.registry.fixtures import *
from test.registry.protocol_fixtures import *

from test.registry.protocols import Failures, Image, layer_bytes_for_contents, ProtocolOptions

from app import instance_keys
from data.registry_model import registry_model
from image.docker.schema1 import DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
from image.docker.schema2 import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
from image.docker.schema2.list import DockerSchema2ManifestListBuilder
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.oci.index import OCIIndexBuilder
from util.security.registry_jwt import decode_bearer_header
from util.timedeltastring import convert_to_timedelta


def test_basic_push_pull(pusher, puller, basic_images, liveserver_session, app_reloader):
    """ Test: Basic push and pull of an image to a new repository. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )


def test_empty_layer(pusher, puller, images_with_empty_layer, liveserver_session, app_reloader):
    """ Test: Push and pull of an image with an empty layer to a new repository. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images_with_empty_layer,
        credentials=credentials,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images_with_empty_layer,
        credentials=credentials,
    )


def test_empty_layer_push_again(
    pusher, puller, images_with_empty_layer, liveserver_session, app_reloader
):
    """ Test: Push and pull of an image with an empty layer to a new repository and then push it
      again. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images_with_empty_layer,
        credentials=credentials,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images_with_empty_layer,
        credentials=credentials,
    )

    # Push to the repository again, to ensure everything is skipped properly.
    options = ProtocolOptions()
    options.skip_head_checks = True
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images_with_empty_layer,
        credentials=credentials,
        options=options,
    )


def test_multi_layer_images_push_pull(
    pusher, puller, multi_layer_images, liveserver_session, app_reloader
):
    """ Test: Basic push and pull of a multi-layered image to a new repository. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        multi_layer_images,
        credentials=credentials,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        multi_layer_images,
        credentials=credentials,
    )


def test_overwrite_tag(
    pusher, puller, basic_images, different_images, liveserver_session, app_reloader
):
    """ Test: Basic push and pull of an image to a new repository, followed by a push to the same
      tag with different images. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        different_images,
        credentials=credentials,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        different_images,
        credentials=credentials,
    )


def test_basic_push_pull_by_manifest(
    manifest_protocol, basic_images, liveserver_session, app_reloader
):
    """ Test: Basic push and pull-by-manifest of an image to a new repository. """
    credentials = ("devtable", "password")

    # Push a new repository.
    result = manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Pull the repository by digests to verify.
    options = ProtocolOptions()
    options.require_matching_manifest_type = True

    digests = [str(manifest.digest) for manifest in list(result.manifests.values())]
    manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        digests,
        basic_images,
        credentials=credentials,
        options=options,
    )


def test_basic_push_by_manifest_digest(
    manifest_protocol, basic_images, liveserver_session, app_reloader
):
    """ Test: Basic push-by-manifest and pull-by-manifest of an image to a new repository. """
    credentials = ("devtable", "password")

    # Push a new repository.
    options = ProtocolOptions()
    options.push_by_manifest_digest = True

    result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
    )

    # If this is not schema 1, then verify we cannot pull.
    expected_failure = None if manifest_protocol.schema == "schema1" else Failures.UNKNOWN_TAG

    # Pull the repository by digests to verify.
    digests = [str(manifest.digest) for manifest in list(result.manifests.values())]
    manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        digests,
        basic_images,
        credentials=credentials,
        expected_failure=expected_failure,
    )


def test_manifest_down_conversion(
    manifest_protocol, v21_protocol, basic_images, liveserver_session, app_reloader
):
    """ Test: Push using a new protocol and ensure down-conversion. """
    credentials = ("devtable", "password")

    # Push a new repository.
    result = manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Pull the repository with down conversion.
    options = ProtocolOptions()

    v21_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
    )


def test_empty_manifest(v22_protocol, liveserver_session, app_reloader):
    credentials = ("devtable", "password")

    # Push an empty manifest.
    v22_protocol.push(
        liveserver_session, "devtable", "simple", "latest", [], credentials=credentials,
    )

    # Pull the empty manifest.
    v22_protocol.pull(
        liveserver_session, "devtable", "simple", "latest", [], credentials=credentials
    )


def test_push_invalid_credentials(pusher, basic_images, liveserver_session, app_reloader):
    """ Test: Ensure we get auth errors when trying to push with invalid credentials. """
    invalid_credentials = ("devtable", "notcorrectpassword")

    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=invalid_credentials,
        expected_failure=Failures.UNAUTHENTICATED,
    )


def test_pull_invalid_credentials(puller, basic_images, liveserver_session, app_reloader):
    """ Test: Ensure we get auth errors when trying to pull with invalid credentials. """
    invalid_credentials = ("devtable", "notcorrectpassword")

    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=invalid_credentials,
        expected_failure=Failures.UNAUTHENTICATED,
    )


def test_push_pull_formerly_bad_repo_name(
    pusher, puller, basic_images, liveserver_session, app_reloader
):
    """ Test: Basic push and pull of an image to a new repository with a name that formerly
            failed. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session, "devtable", "foo.bar", "latest", basic_images, credentials=credentials
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session, "devtable", "foo.bar", "latest", basic_images, credentials=credentials
    )


def test_application_repo(
    pusher,
    puller,
    basic_images,
    liveserver_session,
    app_reloader,
    registry_server_executor,
    liveserver,
):
    """ Test: Attempting to push or pull from an *application* repository raises a 405. """
    credentials = ("devtable", "password")
    registry_server_executor.on(liveserver).create_app_repository("devtable", "someapprepo")

    # Attempt to push to the repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "someapprepo",
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.APP_REPOSITORY,
    )

    # Attempt to pull from the repository.
    puller.pull(
        liveserver_session,
        "devtable",
        "someapprepo",
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.APP_REPOSITORY,
    )


def test_middle_layer_different_sha(v2_protocol, v1_protocol, liveserver_session, app_reloader):
    """ Test: Pushing of a 3-layer image with the *same* V1 ID's, but the middle layer having
            different bytes, must result in new IDs being generated for the leaf layer, as
            they point to different "images".
  """
    credentials = ("devtable", "password")
    first_images = [
        Image(id="baseimage", parent_id=None, size=None, bytes=layer_bytes_for_contents(b"base")),
        Image(
            id="middleimage",
            parent_id="baseimage",
            size=None,
            bytes=layer_bytes_for_contents(b"middle"),
        ),
        Image(
            id="leafimage",
            parent_id="middleimage",
            size=None,
            bytes=layer_bytes_for_contents(b"leaf"),
        ),
    ]

    # First push and pull the images, to ensure we have the basics setup and working.
    v2_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", first_images, credentials=credentials
    )
    first_pull_result = v2_protocol.pull(
        liveserver_session, "devtable", "newrepo", "latest", first_images, credentials=credentials
    )
    first_manifest = first_pull_result.manifests["latest"]
    assert set([image.id for image in first_images]) == set(first_manifest.image_ids)
    assert first_pull_result.image_ids["latest"] == "leafimage"

    # Next, create an image list with the middle image's *bytes* changed.
    second_images = list(first_images)
    second_images[1] = Image(
        id="middleimage",
        parent_id="baseimage",
        size=None,
        bytes=layer_bytes_for_contents(b"different middle bytes"),
    )

    # Push and pull the image, ensuring that the produced ID for the middle and leaf layers
    # are synthesized.
    options = ProtocolOptions()
    options.skip_head_checks = True

    v2_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        second_images,
        credentials=credentials,
        options=options,
    )
    second_pull_result = v1_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        second_images,
        credentials=credentials,
        options=options,
    )

    assert second_pull_result.image_ids["latest"] != "leafimage"


def add_robot(api_caller, _):
    api_caller.conduct_auth("devtable", "password")
    resp = api_caller.get("/api/v1/organization/buynlarge/robots/ownerbot")
    return ("buynlarge+ownerbot", resp.json()["token"])


def add_token(_, executor):
    return ("$token", executor.add_token().text)


# TODO: Test logging to elastic search log model.
@pytest.mark.parametrize(
    "credentials, namespace, expected_performer, is_public_namespace",
    [
        (("devtable", "password"), "devtable", "devtable", False),
        (("devtable", "password"), "buynlarge", "devtable", False),
        (("devtable", "password"), "sellnsmall", "devtable", True),
        (add_robot, "buynlarge", "buynlarge+ownerbot", False),
        (("$oauthtoken", "%s%s" % ("b" * 40, "c" * 40)), "devtable", "devtable", False),
        (("$app", "%s%s" % ("a" * 60, "b" * 60)), "devtable", "devtable", False),
        (add_token, "devtable", None, False),
    ],
)
@pytest.mark.parametrize("disable_pull_logs", [False, True,])
def test_push_pull_logging(
    credentials,
    namespace,
    expected_performer,
    disable_pull_logs,
    is_public_namespace,
    pusher,
    puller,
    basic_images,
    liveserver_session,
    liveserver,
    api_caller,
    app_reloader,
    registry_server_executor,
):
    """ Test: Basic push and pull, ensuring that logs are added for each operation. """

    with FeatureFlagValue(
        "DISABLE_PULL_LOGS_FOR_FREE_NAMESPACES",
        disable_pull_logs,
        registry_server_executor.on(liveserver),
    ):
        # Create the repository before the test push.
        start_images = [
            Image(
                id="startimage",
                parent_id=None,
                size=None,
                bytes=layer_bytes_for_contents(b"start image"),
            )
        ]
        pusher.push(
            liveserver_session,
            namespace,
            "newrepo",
            "latest",
            start_images,
            credentials=("devtable", "password"),
        )

        # Retrieve the credentials to use. This must be done after the repo is created, because
        # some credentials creation code adds the new entity to the repository.
        if not isinstance(credentials, tuple):
            credentials = credentials(api_caller, registry_server_executor.on(liveserver))

        # Push to the repository with the specified credentials.
        pusher.push(
            liveserver_session,
            namespace,
            "newrepo",
            "anothertag",
            basic_images,
            credentials=credentials,
        )

        # Check the logs for the push.
        api_caller.conduct_auth("devtable", "password")

        result = api_caller.get("/api/v1/repository/%s/newrepo/logs" % namespace)
        logs = result.json()["logs"]
        assert len(logs) == 2
        assert logs[0]["kind"] == "push_repo"
        assert logs[0]["metadata"]["namespace"] == namespace
        assert logs[0]["metadata"]["repo"] == "newrepo"

        if expected_performer is not None:
            assert logs[0]["performer"]["name"] == expected_performer

        # Pull the repository to verify.
        puller.pull(
            liveserver_session,
            namespace,
            "newrepo",
            "anothertag",
            basic_images,
            credentials=credentials,
        )

        # Check the logs for the pull if applicable.
        result = api_caller.get("/api/v1/repository/%s/newrepo/logs" % namespace)
        logs = result.json()["logs"]

        if not disable_pull_logs or not is_public_namespace:
            assert len(logs) == 3
            assert logs[0]["kind"] == "pull_repo"
            assert logs[0]["metadata"]["namespace"] == namespace
            assert logs[0]["metadata"]["repo"] == "newrepo"

            if expected_performer is not None:
                assert logs[0]["performer"]["name"] == expected_performer
        else:
            assert len(logs) == 2
            assert logs[0]["kind"] == "push_repo"


def test_pull_publicrepo_anonymous(
    pusher, puller, basic_images, liveserver_session, app_reloader, api_caller, liveserver
):
    """ Test: Pull a public repository anonymously. """
    # Add a new repository under the public user, so we have a repository to pull.
    pusher.push(
        liveserver_session,
        "public",
        "newrepo",
        "latest",
        basic_images,
        credentials=("public", "password"),
    )

    # First try to pull the (currently private) repo anonymously, which should fail (since it is
    # private)
    puller.pull(
        liveserver_session,
        "public",
        "newrepo",
        "latest",
        basic_images,
        expected_failure=Failures.UNAUTHORIZED,
    )

    # Using a non-public user should also fail.
    puller.pull(
        liveserver_session,
        "public",
        "newrepo",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
        expected_failure=Failures.UNAUTHORIZED,
    )

    # Make the repository public.
    api_caller.conduct_auth("public", "password")
    api_caller.change_repo_visibility("public", "newrepo", "public")

    # Pull the repository anonymously, which should succeed because the repository is public.
    puller.pull(liveserver_session, "public", "newrepo", "latest", basic_images)


def test_pull_publicrepo_no_anonymous_access(
    pusher,
    puller,
    basic_images,
    liveserver_session,
    app_reloader,
    api_caller,
    liveserver,
    registry_server_executor,
):
    """ Test: Attempts to pull a public repository anonymously, with the feature flag disabled. """
    # Add a new repository under the public user, so we have a repository to pull.
    pusher.push(
        liveserver_session,
        "public",
        "newrepo",
        "latest",
        basic_images,
        credentials=("public", "password"),
    )

    # First try to pull the (currently private) repo anonymously, which should fail (since it is
    # private)
    puller.pull(
        liveserver_session,
        "public",
        "newrepo",
        "latest",
        basic_images,
        expected_failure=Failures.UNAUTHORIZED,
    )

    # Using a non-public user should also fail.
    puller.pull(
        liveserver_session,
        "public",
        "newrepo",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
        expected_failure=Failures.UNAUTHORIZED,
    )

    # Make the repository public.
    api_caller.conduct_auth("public", "password")
    api_caller.change_repo_visibility("public", "newrepo", "public")

    with FeatureFlagValue("ANONYMOUS_ACCESS", False, registry_server_executor.on(liveserver)):
        # Attempt again to pull the (now public) repo anonymously, which should fail since
        # the feature flag for anonymous access is turned off.
        options = ProtocolOptions()
        options.attempt_pull_without_token = True

        puller.pull(
            liveserver_session,
            "public",
            "newrepo",
            "latest",
            basic_images,
            expected_failure=Failures.ANONYMOUS_NOT_ALLOWED,
            options=options,
        )

        # Using a non-public user should now succeed.
        puller.pull(
            liveserver_session,
            "public",
            "newrepo",
            "latest",
            basic_images,
            credentials=("devtable", "password"),
        )


def test_basic_organization_flow(pusher, puller, basic_images, liveserver_session, app_reloader):
    """ Test: Basic push and pull of an image to a new repository by members of an organization. """
    # Add a new repository under the organization via the creator user.
    pusher.push(
        liveserver_session,
        "buynlarge",
        "newrepo",
        "latest",
        basic_images,
        credentials=("creator", "password"),
    )

    # Ensure that the creator can pull it.
    puller.pull(
        liveserver_session,
        "buynlarge",
        "newrepo",
        "latest",
        basic_images,
        credentials=("creator", "password"),
    )

    # Ensure that the admin can pull it.
    puller.pull(
        liveserver_session,
        "buynlarge",
        "newrepo",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )

    # Ensure that the reader *cannot* pull it.
    puller.pull(
        liveserver_session,
        "buynlarge",
        "newrepo",
        "latest",
        basic_images,
        credentials=("reader", "password"),
        expected_failure=Failures.UNAUTHORIZED,
    )


def test_library_support(pusher, puller, basic_images, liveserver_session, app_reloader):
    """ Test: Pushing and pulling from the implicit library namespace. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(liveserver_session, "", "newrepo", "latest", basic_images, credentials=credentials)

    # Pull the repository to verify.
    puller.pull(liveserver_session, "", "newrepo", "latest", basic_images, credentials=credentials)

    # Pull the repository from the library namespace to verify.
    puller.pull(
        liveserver_session, "library", "newrepo", "latest", basic_images, credentials=credentials
    )


def test_library_namespace_with_support_disabled(
    pusher,
    puller,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Pushing and pulling from the explicit library namespace, even when the
            implicit one is disabled.
  """
    credentials = ("devtable", "password")

    with FeatureFlagValue("LIBRARY_SUPPORT", False, registry_server_executor.on(liveserver)):
        # Push a new repository.
        pusher.push(
            liveserver_session,
            "library",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
        )

        # Pull the repository from the library namespace to verify.
        puller.pull(
            liveserver_session,
            "library",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
        )


def test_push_library_with_support_disabled(
    pusher, basic_images, liveserver_session, app_reloader, liveserver, registry_server_executor
):
    """ Test: Pushing to the implicit library namespace, when disabled,
            should fail.
  """
    credentials = ("devtable", "password")

    with FeatureFlagValue("LIBRARY_SUPPORT", False, registry_server_executor.on(liveserver)):
        # Attempt to push a new repository.
        pusher.push(
            liveserver_session,
            "",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
            expected_failure=Failures.DISALLOWED_LIBRARY_NAMESPACE,
        )


def test_pull_library_with_support_disabled(
    puller, basic_images, liveserver_session, app_reloader, liveserver, registry_server_executor
):
    """ Test: Pushing to the implicit library namespace, when disabled,
            should fail.
  """
    credentials = ("devtable", "password")

    with FeatureFlagValue("LIBRARY_SUPPORT", False, registry_server_executor.on(liveserver)):
        # Attempt to pull the repository from the library namespace.
        puller.pull(
            liveserver_session,
            "",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
            expected_failure=Failures.DISALLOWED_LIBRARY_NAMESPACE,
        )


def test_image_replication(
    pusher,
    puller,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Ensure that entries are created for replication of the images pushed. """
    credentials = ("devtable", "password")

    with FeatureFlagValue("STORAGE_REPLICATION", True, registry_server_executor.on(liveserver)):
        pusher.push(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
        )

        result = puller.pull(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
        )

        # Ensure that entries were created for each layer.
        r = registry_server_executor.on(liveserver).verify_replication_for(
            "devtable", "newrepo", "latest"
        )
        assert r.text == "OK"


def test_image_replication_empty_layers(
    pusher,
    puller,
    images_with_empty_layer,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Ensure that entries are created for replication of the images pushed. """
    credentials = ("devtable", "password")

    with FeatureFlagValue("STORAGE_REPLICATION", True, registry_server_executor.on(liveserver)):
        pusher.push(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            images_with_empty_layer,
            credentials=credentials,
        )

        result = puller.pull(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            images_with_empty_layer,
            credentials=credentials,
        )

        # Ensure that entries were created for each layer.
        r = registry_server_executor.on(liveserver).verify_replication_for(
            "devtable", "newrepo", "latest"
        )
        assert r.text == "OK"


@pytest.mark.parametrize(
    "repo_name, expected_failure",
    [
        ("something", None),
        ("some/slash", Failures.SLASH_REPOSITORY),
        pytest.param("x" * 255, None, id="Valid long name"),
        pytest.param("x" * 256, Failures.INVALID_REPOSITORY, id="Name too long"),
    ],
)
def test_push_reponame(
    repo_name, expected_failure, pusher, puller, basic_images, liveserver_session, app_reloader
):
    """ Test: Attempt to add a repository with various names.
  """
    credentials = ("devtable", "password")

    pusher.push(
        liveserver_session,
        "devtable",
        repo_name,
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=expected_failure,
    )

    if expected_failure is None:
        puller.pull(
            liveserver_session,
            "devtable",
            repo_name,
            "latest",
            basic_images,
            credentials=credentials,
        )


@pytest.mark.parametrize(
    "tag_name, expected_failure",
    [
        ("l", None),
        ("1", None),
        ("x" * 128, None),
        ("", Failures.MISSING_TAG),
        ("x" * 129, Failures.INVALID_TAG),
        (".fail", Failures.INVALID_TAG),
        ("-fail", Failures.INVALID_TAG),
    ],
)
def test_tag_validaton(
    tag_name, expected_failure, pusher, basic_images, liveserver_session, app_reloader
):
    """ Test: Various forms of tags and whether they succeed or fail as expected. """
    credentials = ("devtable", "password")

    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        tag_name,
        basic_images,
        credentials=credentials,
        expected_failure=expected_failure,
    )


def test_invalid_parent(legacy_pusher, liveserver_session, app_reloader):
    """ Test: Attempt to push an image with an invalid/missing parent. """
    images = [
        Image(
            id="childimage",
            parent_id="parentimage",
            size=None,
            bytes=layer_bytes_for_contents(b"child"),
        ),
    ]

    credentials = ("devtable", "password")

    legacy_pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        expected_failure=Failures.INVALID_IMAGES,
    )


def test_wrong_image_order(legacy_pusher, liveserver_session, app_reloader):
    """ Test: Attempt to push an image with its layers in the wrong order. """
    images = [
        Image(
            id="childimage",
            parent_id="parentimage",
            size=None,
            bytes=layer_bytes_for_contents(b"child"),
        ),
        Image(
            id="parentimage", parent_id=None, size=None, bytes=layer_bytes_for_contents(b"parent")
        ),
    ]

    credentials = ("devtable", "password")

    legacy_pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        expected_failure=Failures.INVALID_IMAGES,
    )


@pytest.mark.parametrize(
    "labels",
    [
        # Basic labels.
        [("foo", "bar", "text/plain"), ("baz", "meh", "text/plain")],
        # Theoretically invalid, but allowed when pushed via registry protocol.
        [("theoretically-invalid--label", "foo", "text/plain")],
        # JSON label.
        [("somejson", '{"some": "json"}', "application/json"), ("plain", "", "text/plain")],
        # JSON-esque (but not valid JSON) labels.
        [("foo", "[hello world]", "text/plain"), ("bar", "{wassup?!}", "text/plain")],
        # Empty key label.
        [("", "somevalue", "text/plain")],
    ],
)
def test_labels(labels, manifest_protocol, liveserver_session, api_caller, app_reloader):
    """ Test: Image pushed with labels has those labels found in the database after the
      push succeeds.
  """
    images = [
        Image(
            id="theimage",
            parent_id=None,
            bytes=layer_bytes_for_contents(b"image"),
            config={"Labels": {key: value for (key, value, _) in labels}},
        ),
    ]

    credentials = ("devtable", "password")
    result = manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", images, credentials=credentials
    )

    digest = result.manifests["latest"].digest
    api_caller.conduct_auth("devtable", "password")

    data = api_caller.get("/api/v1/repository/devtable/newrepo/manifest/%s/labels" % digest).json()
    labels_found = data["labels"]
    assert len(labels_found) == len([label for label in labels if label[0]])

    labels_found_map = {l["key"]: l for l in labels_found}
    assert set([k for k in images[0].config["Labels"].keys() if k]) == set(labels_found_map.keys())

    for key, _, media_type in labels:
        if key:
            assert labels_found_map[key]["source_type"] == "manifest"
            assert labels_found_map[key]["media_type"] == media_type


@pytest.mark.parametrize(
    "label_value, expected_expiration",
    [("1d", True), ("1h", True), ("2w", True), ("1g", False), ("something", False),],
)
def test_expiration_label(
    label_value,
    expected_expiration,
    manifest_protocol,
    liveserver_session,
    api_caller,
    app_reloader,
):
    """ Test: Tag pushed with a valid `quay.expires-after` will have its expiration set to its
            start time plus the duration specified. If the duration is invalid, no expiration will
            be set.
  """
    images = [
        Image(
            id="theimage",
            parent_id=None,
            bytes=layer_bytes_for_contents(b"image"),
            config={"Labels": {"quay.expires-after": label_value}},
        ),
    ]

    credentials = ("devtable", "password")
    manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", images, credentials=credentials
    )

    api_caller.conduct_auth("devtable", "password")

    tag_data = api_caller.get("/api/v1/repository/devtable/newrepo/tag").json()["tags"][0]
    if expected_expiration:
        diff = convert_to_timedelta(label_value).total_seconds()
        assert tag_data["end_ts"] == tag_data["start_ts"] + diff
    else:
        assert tag_data.get("end_ts") is None


def test_invalid_blob_reference(manifest_protocol, basic_images, liveserver_session, app_reloader):
    """ Test: Attempt to push a manifest with an invalid blob reference. """
    credentials = ("devtable", "password")

    options = ProtocolOptions()
    options.manifest_invalid_blob_references = True

    # Attempt to push a new repository.
    manifest_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
        expected_failure=Failures.INVALID_BLOB,
    )


def test_delete_tag(
    pusher, puller, basic_images, different_images, liveserver_session, app_reloader
):
    """ Test: Push a repository, delete a tag, and attempt to pull. """
    credentials = ("devtable", "password")

    # Push the tags.
    result = pusher.push(
        liveserver_session, "devtable", "newrepo", "one", basic_images, credentials=credentials
    )

    pusher.push(
        liveserver_session, "devtable", "newrepo", "two", different_images, credentials=credentials
    )

    # Delete tag `one` by digest or tag.
    pusher.delete(
        liveserver_session,
        "devtable",
        "newrepo",
        result.manifests["one"].digest if result.manifests else "one",
        credentials=credentials,
    )

    # Attempt to pull tag `one` and ensure it doesn't work.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "one",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.UNKNOWN_TAG,
    )

    # Pull tag `two` to verify it works.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "two", different_images, credentials=credentials
    )


def test_delete_manifest(
    manifest_protocol, puller, basic_images, different_images, liveserver_session, app_reloader
):
    """ Test: Push a tag, push the tag again, push it back to the original manifest,
            delete the tag, verify cannot pull. """
    credentials = ("devtable", "password")
    options = ProtocolOptions()
    options.skip_head_checks = True

    # Push the latest tag.
    manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Verify.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Necessary for older data model.
    time.sleep(2)

    # Push the latest tag to a different manifest.
    manifest_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        different_images,
        credentials=credentials,
        options=options,
    )

    # Verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        different_images,
        credentials=credentials,
    )

    # Necessary for older data model.
    time.sleep(2)

    # Push the latest tag back to the original images.
    result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
    )

    # Verify.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Necessary for older data model.
    time.sleep(2)

    # Delete the basic images manifest.
    manifest_protocol.delete(
        liveserver_session,
        "devtable",
        "newrepo",
        result.manifests["latest"].digest,
        credentials=credentials,
    )

    # Attempt to pull tag `latest` and ensure it doesn't work.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.UNKNOWN_TAG,
    )


def test_cancel_upload(manifest_protocol, basic_images, liveserver_session, app_reloader):
    """ Test: Cancelation of blob uploads. """
    credentials = ("devtable", "password")

    options = ProtocolOptions()
    options.cancel_blob_upload = True

    manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )


def test_blob_caching(
    manifest_protocol,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Pulling of blobs after initially pulled will result in the blobs being cached. """
    credentials = ("devtable", "password")

    # Push a tag.
    result = manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Conduct the initial pull to prime the cache.
    manifest_protocol.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Disconnect the server from the database.
    registry_server_executor.on(liveserver).break_database()

    # Pull each blob, which should succeed due to caching. If caching is broken, this will
    # fail when it attempts to hit the database.
    for blob_id in result.manifests["latest"].local_blob_digests:
        r = liveserver_session.get(
            "/v2/devtable/newrepo/blobs/%s" % blob_id, headers=result.headers
        )
        assert r.status_code == 200


@pytest.mark.parametrize(
    "chunks",
    [
        # Two chunks.
        [(0, 100), (100, None)],
        # Multiple chunks.
        [(0, 10), (10, 20), (20, None)],
        [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, None)],
        # Overlapping chunks.
        [(0, 90), (10, None)],
    ],
)
def test_chunked_blob_uploading(
    chunks, random_layer_data, v21_protocol, puller, liveserver_session, app_reloader
):
    """ Test: Uploading of blobs as chunks. """
    credentials = ("devtable", "password")

    adjusted_chunks = []
    for start_byte, end_byte in chunks:
        adjusted_chunks.append((start_byte, end_byte if end_byte else len(random_layer_data)))

    images = [
        Image(id="theimage", parent_id=None, bytes=random_layer_data),
    ]

    options = ProtocolOptions()
    options.chunks_for_upload = adjusted_chunks

    # Push the image, using the specified chunking.
    v21_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        options=options,
    )

    # Pull to verify the image was created.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "latest", images, credentials=credentials
    )


def test_chunked_uploading_mismatched_chunks(
    v21_protocol, random_layer_data, liveserver_session, app_reloader
):
    """ Test: Attempt to upload chunks with data missing. """
    credentials = ("devtable", "password")

    images = [
        Image(id="theimage", parent_id=None, bytes=random_layer_data),
    ]

    # Note: Byte #100 is missing.
    options = ProtocolOptions()
    options.chunks_for_upload = [(0, 100), (101, len(random_layer_data), 416)]

    # Attempt to push, with the chunked upload failing.
    v21_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        options=options,
    )


def test_chunked_uploading_missing_first_chunk(
    v2_protocol, random_layer_data, liveserver_session, app_reloader
):
    """ Test: Attempt to upload a chunk with missing data.. """
    credentials = ("devtable", "password")

    images = [
        Image(id="theimage", parent_id=None, bytes=random_layer_data),
    ]

    # Note: First 10 bytes are missing.
    options = ProtocolOptions()
    options.chunks_for_upload = [(10, len(random_layer_data), 416)]

    # Attempt to push, with the chunked upload failing.
    v2_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        options=options,
    )


def test_pull_disabled_namespace(
    pusher,
    puller,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Attempt to pull a repository from a disabled namespace results in an error. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "buynlarge",
        "someneworgrepo",
        "latest",
        basic_images,
        credentials=credentials,
    )

    # Disable the namespace.
    registry_server_executor.on(liveserver).disable_namespace("buynlarge")

    # Attempt to pull, which should fail.
    puller.pull(
        liveserver_session,
        "buynlarge",
        "someneworgrepo",
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.NAMESPACE_DISABLED,
    )


def test_push_disabled_namespace(
    pusher, basic_images, liveserver_session, app_reloader, liveserver, registry_server_executor
):
    """ Test: Attempt to push a repository from a disabled namespace results in an error. """
    credentials = ("devtable", "password")

    # Disable the namespace.
    registry_server_executor.on(liveserver).disable_namespace("buynlarge")

    # Attempt to push, which should fail.
    pusher.push(
        liveserver_session,
        "buynlarge",
        "someneworgrepo",
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.NAMESPACE_DISABLED,
    )


def test_private_catalog_no_access(
    v2_protocol, liveserver_session, app_reloader, liveserver, registry_server_executor
):
    """ Test: Ensure that accessing a private catalog with anonymous access results in no database
      connections.
  """
    with FeatureFlagValue("PUBLIC_CATALOG", False, registry_server_executor.on(liveserver)):
        # Disconnect the server from the database.
        registry_server_executor.on(liveserver).break_database()

        results = v2_protocol.catalog(liveserver_session)
        assert not results


@pytest.mark.parametrize(
    "public_catalog, credentials, expected_repos",
    [
        # No public access and no credentials => No results.
        (False, None, None),
        # Public access and no credentials => public repositories.
        (True, None, ["public/publicrepo"]),
        # Private creds => private repositories.
        (
            False,
            ("devtable", "password"),
            ["devtable/simple", "devtable/complex", "devtable/gargantuan"],
        ),
        (
            True,
            ("devtable", "password"),
            ["devtable/simple", "devtable/complex", "devtable/gargantuan"],
        ),
    ],
)
@pytest.mark.parametrize("page_size", [1, 2, 10, 50, 100,])
def test_catalog(
    public_catalog,
    credentials,
    expected_repos,
    page_size,
    v2_protocol,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Retrieving results from the V2 catalog. """
    with FeatureFlagValue(
        "PUBLIC_CATALOG", public_catalog, registry_server_executor.on(liveserver)
    ):
        results = v2_protocol.catalog(
            liveserver_session,
            page_size=page_size,
            credentials=credentials,
            namespace="devtable",
            repo_name="simple",
        )

    if expected_repos is None:
        assert len(results) == 0
    else:
        assert set(expected_repos).issubset(set(results))


def test_catalog_caching(
    v2_protocol,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Calling the catalog after initially pulled will result in the catalog being cached. """
    credentials = ("devtable", "password")

    # Conduct the initial catalog call to prime the cache.
    results = v2_protocol.catalog(
        liveserver_session, credentials=credentials, namespace="devtable", repo_name="simple"
    )

    token, _ = v2_protocol.auth(liveserver_session, credentials, "devtable", "simple")

    # Disconnect the server from the database.
    registry_server_executor.on(liveserver).break_database()

    # Call the catalog again, which should now be cached.
    cached_results = v2_protocol.catalog(liveserver_session, bearer_token=token)
    assert len(cached_results) == len(results)
    assert set(cached_results) == set(results)


def test_catalog_disabled_namespace(
    v2_protocol,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    credentials = ("devtable", "password")

    # Get a valid token.
    token, _ = v2_protocol.auth(liveserver_session, credentials, "devtable", "simple")

    # Disable the devtable namespace.
    registry_server_executor.on(liveserver).disable_namespace("devtable")

    # Try to retrieve the catalog and ensure it fails to return any results.
    results = v2_protocol.catalog(liveserver_session, bearer_token=token)
    assert len(results) == 0


@pytest.mark.parametrize(
    "username, namespace, repository",
    [
        ("devtable", "devtable", "simple"),
        ("devtable", "devtable", "gargantuan"),
        ("public", "public", "publicrepo"),
        ("devtable", "buynlarge", "orgrepo"),
    ],
)
@pytest.mark.parametrize("page_size", [1, 2, 10, 50, 100,])
def test_tags(
    username,
    namespace,
    repository,
    page_size,
    v2_protocol,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    """ Test: Retrieving results from the V2 catalog. """
    credentials = (username, "password")
    results = v2_protocol.tags(
        liveserver_session,
        page_size=page_size,
        credentials=credentials,
        namespace=namespace,
        repo_name=repository,
    )

    repo_ref = registry_model.lookup_repository(namespace, repository)
    expected_tags = [tag.name for tag in registry_model.list_all_active_repository_tags(repo_ref)]
    assert len(results) == len(expected_tags)
    assert set([r for r in results]) == set(expected_tags)

    # Invoke the tags endpoint again to ensure caching works.
    results = v2_protocol.tags(
        liveserver_session,
        page_size=page_size,
        credentials=credentials,
        namespace=namespace,
        repo_name=repository,
    )
    assert len(results) == len(expected_tags)
    assert set([r for r in results]) == set(expected_tags)


def test_tags_disabled_namespace(
    v2_protocol,
    basic_images,
    liveserver_session,
    app_reloader,
    liveserver,
    registry_server_executor,
):
    credentials = ("devtable", "password")

    # Disable the buynlarge namespace.
    registry_server_executor.on(liveserver).disable_namespace("buynlarge")

    # Try to retrieve the tags and ensure it fails.
    v2_protocol.tags(
        liveserver_session,
        credentials=credentials,
        namespace="buynlarge",
        repo_name="orgrepo",
        expected_failure=Failures.NAMESPACE_DISABLED,
    )


@pytest.mark.parametrize(
    "push_user, push_namespace, push_repo, mount_repo_name, expected_failure",
    [
        # Successful mount, same namespace.
        ("devtable", "devtable", "baserepo", "devtable/baserepo", None),
        # Successful mount, cross namespace.
        ("devtable", "buynlarge", "baserepo", "buynlarge/baserepo", None),
        # Unsuccessful mount, unknown repo.
        ("devtable", "devtable", "baserepo", "unknown/repohere", Failures.UNAUTHORIZED_FOR_MOUNT),
        # Unsuccessful mount, no access.
        ("public", "public", "baserepo", "public/baserepo", Failures.UNAUTHORIZED_FOR_MOUNT),
    ],
)
def test_blob_mounting(
    push_user,
    push_namespace,
    push_repo,
    mount_repo_name,
    expected_failure,
    manifest_protocol,
    pusher,
    puller,
    basic_images,
    liveserver_session,
    app_reloader,
):
    # Push an image so we can attempt to mount it.
    pusher.push(
        liveserver_session,
        push_namespace,
        push_repo,
        "latest",
        basic_images,
        credentials=(push_user, "password"),
    )

    # Push again, trying to mount the image layer(s) from the mount repo.
    options = ProtocolOptions()
    options.scopes = [
        "repository:devtable/newrepo:push,pull",
        "repository:%s:pull" % (mount_repo_name),
    ]
    options.mount_blobs = {
        "sha256:" + hashlib.sha256(image.bytes).hexdigest(): mount_repo_name
        for image in basic_images
    }

    manifest_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
        options=options,
        expected_failure=expected_failure,
    )

    if expected_failure is None:
        # Pull to ensure it worked.
        puller.pull(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            basic_images,
            credentials=("devtable", "password"),
        )


def test_blob_mounting_with_empty_layers(
    manifest_protocol, pusher, puller, images_with_empty_layer, liveserver_session, app_reloader
):
    # Push an image so we can attempt to mount it.
    pusher.push(
        liveserver_session,
        "devtable",
        "simple",
        "latest",
        images_with_empty_layer,
        credentials=("devtable", "password"),
    )

    # Push again, trying to mount the image layer(s) from the mount repo.
    options = ProtocolOptions()
    options.scopes = [
        "repository:devtable/newrepo:push,pull",
        "repository:%s:pull" % ("devtable/simple"),
    ]
    options.mount_blobs = {
        "sha256:" + hashlib.sha256(image.bytes).hexdigest(): "devtable/simple"
        for image in images_with_empty_layer
    }
    options.skip_head_checks = True

    manifest_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images_with_empty_layer,
        credentials=("devtable", "password"),
        options=options,
    )


def get_robot_password(api_caller, username="ownerbot", namespace="buynlarge"):
    api_caller.conduct_auth("devtable", "password")

    if namespace == "buynlarge":
        url = "/api/v1/organization/%s/robots/%s" % (namespace, username)

    # devtable is a User, not an organization. Use a different endpoint
    elif namespace == "devtable":
        url = "/api/v1/user/robots/%s" % username

    else:
        raise NotImplementedError("Other robots have not been implemented for this test.")

    resp = api_caller.get(url)
    return resp.json()["token"]


def get_encrypted_password(api_caller):
    api_caller.conduct_auth("devtable", "password")
    resp = api_caller.post(
        "/api/v1/user/clientkey",
        data=json.dumps(dict(password="password")),
        headers={"Content-Type": "application/json"},
    )
    return resp.json()["key"]


@pytest.mark.parametrize(
    "username, password, expect_success",
    [
        # Invalid username.
        ("invaliduser", "somepassword", False),
        # Invalid password.
        ("devtable", "invalidpassword", False),
        # Invalid OAuth token.
        ("$oauthtoken", "unknown", False),
        # Invalid CLI token.
        ("$app", "invalid", False),
        # Valid.
        ("devtable", "password", True),
        # Robot.
        ("buynlarge+ownerbot", get_robot_password, True),
        # Encrypted password.
        ("devtable", get_encrypted_password, True),
        # OAuth.
        ("$oauthtoken", "%s%s" % ("b" * 40, "c" * 40), True),
        # CLI Token.
        ("$app", "%s%s" % ("a" * 60, "b" * 60), True),
    ],
)
def test_login(
    username, password, expect_success, loginer, liveserver_session, api_caller, app_reloader
):
    """ Test: Login flow. """
    if not isinstance(password, str):
        password = password(api_caller)

    loginer.login(liveserver_session, username, password, [], expect_success)


@pytest.mark.parametrize(
    "username, password, scopes, expected_access, expect_success",
    [
        # No scopes.
        ("devtable", "password", [], [], True),
        # Basic pull.
        (
            "devtable",
            "password",
            ["repository:devtable/simple:pull"],
            [{"type": "repository", "name": "devtable/simple", "actions": ["pull"]},],
            True,
        ),
        # Basic push.
        (
            "devtable",
            "password",
            ["repository:devtable/simple:push"],
            [{"type": "repository", "name": "devtable/simple", "actions": ["push"]},],
            True,
        ),
        # Basic push/pull.
        (
            "devtable",
            "password",
            ["repository:devtable/simple:push,pull"],
            [{"type": "repository", "name": "devtable/simple", "actions": ["push", "pull"]},],
            True,
        ),
        # Admin.
        (
            "devtable",
            "password",
            ["repository:devtable/simple:push,pull,*"],
            [{"type": "repository", "name": "devtable/simple", "actions": ["push", "pull", "*"]},],
            True,
        ),
        # Basic pull with endpoint.
        (
            "devtable",
            "password",
            ["repository:localhost:5000/devtable/simple:pull"],
            [
                {
                    "type": "repository",
                    "name": "localhost:5000/devtable/simple",
                    "actions": ["pull"],
                },
            ],
            True,
        ),
        # Basic pull with invalid endpoint.
        ("devtable", "password", ["repository:someinvalid/devtable/simple:pull"], [], False),
        # Pull with no access.
        (
            "public",
            "password",
            ["repository:devtable/simple:pull"],
            [{"type": "repository", "name": "devtable/simple", "actions": []},],
            True,
        ),
        # Anonymous push and pull on a private repository.
        (
            "",
            "",
            ["repository:devtable/simple:pull,push"],
            [{"type": "repository", "name": "devtable/simple", "actions": []},],
            True,
        ),
        # Pull and push with no push access.
        (
            "reader",
            "password",
            ["repository:buynlarge/orgrepo:pull,push"],
            [{"type": "repository", "name": "buynlarge/orgrepo", "actions": ["pull"]},],
            True,
        ),
        # OAuth.
        (
            "$oauthtoken",
            "%s%s" % ("b" * 40, "c" * 40),
            ["repository:public/publicrepo:pull,push"],
            [{"type": "repository", "name": "public/publicrepo", "actions": ["pull"]},],
            True,
        ),
        # Anonymous public repo.
        (
            "",
            "",
            ["repository:public/publicrepo:pull,push"],
            [{"type": "repository", "name": "public/publicrepo", "actions": ["pull"]},],
            True,
        ),
        # Multiple scopes.
        (
            "devtable",
            "password",
            ["repository:devtable/simple:push,pull,*", "repository:buynlarge/orgrepo:pull"],
            [
                {"type": "repository", "name": "devtable/simple", "actions": ["push", "pull", "*"]},
                {"type": "repository", "name": "buynlarge/orgrepo", "actions": ["pull"]},
            ],
            True,
        ),
        # Multiple scopes.
        (
            "devtable",
            "password",
            ["repository:devtable/simple:push,pull,*", "repository:public/publicrepo:push,pull"],
            [
                {"type": "repository", "name": "devtable/simple", "actions": ["push", "pull", "*"]},
                {"type": "repository", "name": "public/publicrepo", "actions": ["pull"]},
            ],
            True,
        ),
        # Read-Only only allows Pulls
        (
            "devtable",
            "password",
            ["repository:devtable/readonly:pull,push,*"],
            [{"type": "repository", "name": "devtable/readonly", "actions": ["pull"]},],
            True,
        ),
        # Mirror only allows Pulls
        (
            "devtable",
            "password",
            ["repository:devtable/mirrored:pull,push,*"],
            [{"type": "repository", "name": "devtable/mirrored", "actions": ["pull"]},],
            True,
        ),
        # Mirror State as specified Robot --> Allow Pushes
        (
            "devtable+dtrobot",
            get_robot_password,
            ["repository:devtable/mirrored:push,pull,*"],
            [{"type": "repository", "name": "devtable/mirrored", "actions": ["push", "pull"]},],
            True,
        ),
        # Mirror State as a Robot w/ write permissions but not the assigned Robot -> No pushes
        (
            "devtable+dtrobot2",
            get_robot_password,
            ["repository:devtable/mirrored:push,pull,*"],
            [{"type": "repository", "name": "devtable/mirrored", "actions": ["pull"]},],
            True,
        ),
        # TODO: Add: mirror state with no robot but the robot has write permissions -> no pushes
    ],
)
def test_login_scopes(
    username,
    password,
    scopes,
    expected_access,
    expect_success,
    v2_protocol,
    liveserver_session,
    api_caller,
    app_reloader,
):
    """ Test: Login via the V2 auth protocol reacts correctly to requested scopes. """
    if not isinstance(password, str):
        robot_namespace, robot_username = username.split("+")
        password = password(api_caller, namespace=robot_namespace, username=robot_username)

    response = v2_protocol.login(liveserver_session, username, password, scopes, expect_success)
    if not expect_success:
        return

    # Validate the returned token.
    encoded = response.json()["token"]
    payload = decode_bearer_header(
        "Bearer " + encoded, instance_keys, {"SERVER_HOSTNAME": "localhost:5000"}
    )
    assert payload is not None
    assert payload["access"] == expected_access


def test_push_pull_same_blobs(pusher, puller, liveserver_session, app_reloader):
    """ Test: Push and pull of an image to a new repository where a blob is shared between layers. """
    credentials = ("devtable", "password")

    layer_bytes = layer_bytes_for_contents(b"some contents")
    images = [
        Image(id="parentid", bytes=layer_bytes, parent_id=None),
        Image(id="someid", bytes=layer_bytes, parent_id="parentid"),
    ]

    options = ProtocolOptions()
    options.skip_head_checks = True  # Since the blob will already exist.

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        options=options,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        images,
        credentials=credentials,
        options=options,
    )


def test_push_tag_existing_image(v1_protocol, basic_images, liveserver_session, app_reloader):
    """ Test: Push a new tag on an existing image. """
    credentials = ("devtable", "password")

    # Push a new repository.
    v1_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Pull the repository to verify.
    pulled = v1_protocol.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials,
    )
    assert pulled.image_ids

    # Push the same image to another tag in the repository.
    v1_protocol.tag(
        liveserver_session,
        "devtable",
        "newrepo",
        "anothertag",
        pulled.image_ids["latest"],
        credentials=credentials,
    )

    # Pull the repository to verify.
    v1_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "anothertag",
        basic_images,
        credentials=credentials,
    )


@pytest.mark.parametrize("schema_version", [1, 2,])
@pytest.mark.parametrize("is_amd", [True, False])
@pytest.mark.parametrize("oci_list", [True, False])
def test_push_pull_manifest_list_back_compat(
    v22_protocol,
    legacy_puller,
    basic_images,
    different_images,
    liveserver_session,
    app_reloader,
    schema_version,
    data_model,
    is_amd,
    oci_list,
):
    """ Test: Push a new tag with a manifest list containing two manifests, one (possibly) legacy
      and one not, and, if there is a legacy manifest, ensure it can be pulled.
  """
    credentials = ("devtable", "password")
    options = ProtocolOptions()

    # Build the manifests that will go in the list.
    blobs = {}

    signed = v22_protocol.build_schema1(
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        blobs,
        options,
        arch="amd64" if is_amd else "something",
    )

    if not oci_list:
        first_manifest = signed.unsigned()
        if schema_version == 2:
            first_manifest = v22_protocol.build_schema2(basic_images, blobs, options)

        second_manifest = v22_protocol.build_schema2(different_images, blobs, options)
    else:
        first_manifest = v22_protocol.build_oci(basic_images, blobs, options)
        second_manifest = v22_protocol.build_oci(different_images, blobs, options)

    # Create and push the manifest list.
    builder = OCIIndexBuilder() if oci_list else DockerSchema2ManifestListBuilder()
    builder.add_manifest(first_manifest, "amd64" if is_amd else "something", "linux")
    builder.add_manifest(second_manifest, "arm", "linux")
    manifestlist = builder.build()

    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [first_manifest, second_manifest],
        blobs,
        credentials=credentials,
        options=options,
    )

    # Pull the tag and ensure we (don't) get back the basic images, since they are(n't) part of the
    # amd64+linux manifest.
    legacy_puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        expected_failure=Failures.UNKNOWN_TAG if not is_amd else None,
    )


@pytest.mark.parametrize("schema_version", [1, 2, "oci"])
def test_push_pull_manifest_list(
    v22_protocol,
    basic_images,
    different_images,
    liveserver_session,
    app_reloader,
    schema_version,
    data_model,
):
    """ Test: Push a new tag with a manifest list containing two manifests, one (possibly) legacy
      and one not, and pull it.
  """
    credentials = ("devtable", "password")
    options = ProtocolOptions()

    # Build the manifests that will go in the list.
    blobs = {}

    signed = v22_protocol.build_schema1(
        "devtable", "newrepo", "latest", basic_images, blobs, options
    )

    if schema_version == "oci":
        first_manifest = v22_protocol.build_oci(basic_images, blobs, options)
        second_manifest = v22_protocol.build_oci(different_images, blobs, options)
    else:
        first_manifest = signed.unsigned()
        if schema_version == 2:
            first_manifest = v22_protocol.build_schema2(basic_images, blobs, options)

        second_manifest = v22_protocol.build_schema2(different_images, blobs, options)

    # Create and push the manifest list.
    builder = OCIIndexBuilder() if schema_version == "oci" else DockerSchema2ManifestListBuilder()
    builder.add_manifest(first_manifest, "amd64", "linux")
    builder.add_manifest(second_manifest, "arm", "linux")
    manifestlist = builder.build()

    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [first_manifest, second_manifest],
        blobs,
        credentials=credentials,
        options=options,
    )

    # Pull and verify the manifest list.
    v22_protocol.pull_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        credentials=credentials,
        options=options,
    )


def test_push_pull_manifest_remote_layers(
    v22_protocol, legacy_puller, liveserver_session, app_reloader, remote_images, data_model
):
    """ Test: Push a new tag with a manifest which contains at least one remote layer, and then
      pull that manifest back.
  """
    credentials = ("devtable", "password")

    # Push a new repository.
    v22_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", remote_images, credentials=credentials
    )

    # Pull the repository to verify.
    v22_protocol.pull(
        liveserver_session, "devtable", "newrepo", "latest", remote_images, credentials=credentials
    )

    # Ensure that the image cannot be pulled by a legacy protocol.
    legacy_puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        remote_images,
        credentials=credentials,
        expected_failure=Failures.UNKNOWN_TAG,
    )


def test_push_manifest_list_missing_manifest(
    v22_protocol, basic_images, liveserver_session, app_reloader, data_model
):
    """ Test: Attempt to push a new tag with a manifest list containing an invalid manifest.
  """
    credentials = ("devtable", "password")
    options = ProtocolOptions()

    # Build the manifests that will go in the list.
    blobs = {}
    manifest = v22_protocol.build_schema2(basic_images, blobs, options)

    # Create and push the manifest list, but without the manifest itself.
    builder = DockerSchema2ManifestListBuilder()
    builder.add_manifest(manifest, "amd64", "linux")
    manifestlist = builder.build()

    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [],
        blobs,
        credentials=credentials,
        options=options,
        expected_failure=Failures.INVALID_MANIFEST_IN_LIST,
    )


def test_push_pull_manifest_list_again(
    v22_protocol, basic_images, different_images, liveserver_session, app_reloader, data_model
):
    """ Test: Push a new tag with a manifest list containing two manifests, push it again, and pull
      it.
  """
    credentials = ("devtable", "password")
    options = ProtocolOptions()

    # Build the manifests that will go in the list.
    blobs = {}

    first_manifest = v22_protocol.build_schema2(basic_images, blobs, options)
    second_manifest = v22_protocol.build_schema2(different_images, blobs, options)

    # Create and push the manifest list.
    builder = DockerSchema2ManifestListBuilder()
    builder.add_manifest(first_manifest, "amd64", "linux")
    builder.add_manifest(second_manifest, "arm", "linux")
    manifestlist = builder.build()

    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [first_manifest, second_manifest],
        blobs,
        credentials=credentials,
        options=options,
    )

    # Push the manifest list again. This should more or less no-op.
    options.skip_head_checks = True
    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [first_manifest, second_manifest],
        blobs,
        credentials=credentials,
        options=options,
    )

    # Pull and verify the manifest list.
    v22_protocol.pull_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        credentials=credentials,
        options=options,
    )


def test_push_pull_manifest_list_duplicate_manifest(
    v22_protocol, basic_images, liveserver_session, app_reloader, data_model
):
    """ Test: Push a manifest list that contains the same child manifest twice.
  """
    credentials = ("devtable", "password")
    options = ProtocolOptions()

    # Build the manifest that will go in the list.
    blobs = {}
    manifest = v22_protocol.build_schema2(basic_images, blobs, options)

    # Create and push the manifest list.
    builder = DockerSchema2ManifestListBuilder()
    builder.add_manifest(manifest, "amd64", "linux")
    builder.add_manifest(manifest, "amd32", "linux")
    manifestlist = builder.build()

    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [manifest],
        blobs,
        credentials=credentials,
        options=options,
    )

    # Pull and verify the manifest list.
    v22_protocol.pull_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        credentials=credentials,
        options=options,
    )


def test_verify_schema2(
    v22_protocol, basic_images, liveserver_session, liveserver, app_reloader, data_model
):
    """ Test: Ensure that pushing of schema 2 manifests results in a pull of a schema2 manifest. """
    credentials = ("devtable", "password")

    # Push a new repository.
    v22_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Pull the repository to verify.
    result = v22_protocol.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )
    manifest = result.manifests["latest"]
    assert manifest.schema_version == 2


def test_geo_blocking(
    pusher,
    puller,
    basic_images,
    liveserver_session,
    liveserver,
    registry_server_executor,
    app_reloader,
):
    """ Test: Attempt to pull an image from a geoblocked IP address. """
    credentials = ("devtable", "password")
    options = ProtocolOptions()
    options.skip_blob_push_checks = True  # Otherwise, cache gets established.

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
    )

    registry_server_executor.on(liveserver).set_geo_block_for_namespace("devtable", "US")

    # Attempt to pull the repository to verify. This should fail with a 403 due to
    # the geoblocking of the IP being using.
    options = ProtocolOptions()
    options.request_addr = "6.0.0.0"
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
        expected_failure=Failures.GEO_BLOCKED,
    )


@pytest.mark.parametrize("has_amd64_linux", [False, True,])
def test_pull_manifest_list_schema2_only(
    v22_protocol,
    basic_images,
    different_images,
    liveserver_session,
    app_reloader,
    data_model,
    has_amd64_linux,
):
    """ Test: Push a new tag with a manifest list containing two manifests, one schema2 (possibly)
      amd64 and one not, and pull it when only accepting a schema2 manifest type. Since the manifest
      list content type is not being sent, this should return just the manifest (or none if no
      linux+amd64 is present.)
  """
    credentials = ("devtable", "password")

    # Build the manifests that will go in the list.
    options = ProtocolOptions()
    blobs = {}

    first_manifest = v22_protocol.build_schema2(basic_images, blobs, options)
    second_manifest = v22_protocol.build_schema2(different_images, blobs, options)

    # Create and push the manifest list.
    builder = DockerSchema2ManifestListBuilder()
    builder.add_manifest(first_manifest, "amd64" if has_amd64_linux else "amd32", "linux")
    builder.add_manifest(second_manifest, "arm", "linux")
    manifestlist = builder.build()

    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [first_manifest, second_manifest],
        blobs,
        credentials=credentials,
    )

    # Pull and verify the manifest.
    options.accept_mimetypes = [DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE]
    result = v22_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
        expected_failure=None if has_amd64_linux else Failures.UNKNOWN_TAG,
    )

    if has_amd64_linux:
        assert result.manifests["latest"].media_type == DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE


def test_push_pull_unicode(pusher, puller, unicode_images, liveserver_session, app_reloader):
    """ Test: Push an image with unicode inside and then pull it. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session, "devtable", "newrepo", "latest", unicode_images, credentials=credentials
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session, "devtable", "newrepo", "latest", unicode_images, credentials=credentials
    )


def test_push_pull_unicode_direct(pusher, puller, unicode_images, liveserver_session, app_reloader):
    """ Test: Push an image with *unescaped* unicode inside and then pull it. """
    credentials = ("devtable", "password")

    # Turn off automatic unicode encoding when building the manifests.
    options = ProtocolOptions()
    options.ensure_ascii = False

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        unicode_images,
        credentials=credentials,
        options=options,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        unicode_images,
        credentials=credentials,
        options=options,
    )


def test_push_legacy_pull_not_allowed(
    v22_protocol, v1_protocol, remote_images, liveserver_session, app_reloader, data_model
):
    """ Test: Push a V2 Schema 2 manifest and attempt to pull via V1 when there is no assigned legacy
      image.
  """
    credentials = ("devtable", "password")

    # Push a new repository.
    v22_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", remote_images, credentials=credentials
    )

    # Attempt to pull. Should fail with a 404.
    v1_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        remote_images,
        credentials=credentials,
        expected_failure=Failures.UNKNOWN_TAG,
    )


def test_push_pull_emoji_unicode(
    pusher, puller, unicode_emoji_images, liveserver_session, app_reloader
):
    """ Test: Push an image with unicode inside and then pull it. """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        unicode_emoji_images,
        credentials=credentials,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        unicode_emoji_images,
        credentials=credentials,
    )


def test_push_pull_emoji_unicode_direct(
    pusher, puller, unicode_emoji_images, liveserver_session, app_reloader
):
    """ Test: Push an image with *unescaped* unicode inside and then pull it. """
    credentials = ("devtable", "password")

    # Turn off automatic unicode encoding when building the manifests.
    options = ProtocolOptions()
    options.ensure_ascii = False

    # Push a new repository.
    pusher.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        unicode_emoji_images,
        credentials=credentials,
        options=options,
    )

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        unicode_emoji_images,
        credentials=credentials,
        options=options,
    )


@pytest.mark.parametrize("accepted_mimetypes", [[], ["application/json"],])
def test_push_pull_older_mimetype(
    pusher, puller, basic_images, liveserver_session, app_reloader, accepted_mimetypes
):
    """ Test: Push and pull an image, but override the accepted mimetypes to that sent by older
            Docker clients.
  """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Turn off automatic unicode encoding when building the manifests.
    options = ProtocolOptions()
    options.accept_mimetypes = accepted_mimetypes

    # Pull the repository to verify.
    puller.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
    )


def test_attempt_push_mismatched_manifest(
    v22_protocol, basic_images, liveserver_session, app_reloader, data_model
):
    """ Test: Attempt to push a manifest list refering to a schema 1 manifest with a different
      architecture than that specified in the manifest list.
  """
    credentials = ("devtable", "password")
    options = ProtocolOptions()

    # Build the manifest that will go in the list. This will be amd64.
    blobs = {}
    signed = v22_protocol.build_schema1(
        "devtable", "newrepo", "latest", basic_images, blobs, options
    )
    manifest = signed.unsigned()

    # Create the manifest list, but refer to the manifest as arm.
    builder = DockerSchema2ManifestListBuilder()
    builder.add_manifest(manifest, "arm", "linux")
    manifestlist = builder.build()

    # Attempt to push the manifest, which should fail.
    v22_protocol.push_list(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        manifestlist,
        [manifest],
        blobs,
        credentials=credentials,
        options=options,
        expected_failure=Failures.INVALID_MANIFEST_IN_LIST,
    )


@pytest.mark.parametrize("delete_method", ["registry", "api",])
def test_attempt_pull_by_manifest_digest_for_deleted_tag(
    delete_method, manifest_protocol, basic_images, liveserver_session, app_reloader, api_caller
):
    """ Test: Attempt to pull a deleted tag's manifest by digest. """
    credentials = ("devtable", "password")

    # Push a new repository.
    result = manifest_protocol.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )
    digests = [str(manifest.digest) for manifest in list(result.manifests.values())]
    assert len(digests) == 1

    # Ensure we can pull by tag.
    manifest_protocol.pull(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Ensure we can pull by digest.
    manifest_protocol.pull(
        liveserver_session, "devtable", "newrepo", digests[0], basic_images, credentials=credentials
    )

    if delete_method == "api":
        api_caller.conduct_auth("devtable", "password")
        resp = api_caller.delete("/api/v1/repository/devtable/newrepo/tag/latest")
        resp.raise_for_status()
    else:
        # Delete the tag by digest.
        manifest_protocol.delete(
            liveserver_session, "devtable", "newrepo", digests[0], credentials=credentials
        )

    # Attempt to pull from the repository by digests to verify it shows they are not accessible.
    manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "newrepo",
        digests[0],
        basic_images,
        credentials=credentials,
        expected_failure=Failures.UNKNOWN_TAG,
    )


@pytest.mark.parametrize(
    "state, use_robot, create_mirror, expected_failure",
    [
        ("NORMAL", True, True, None),
        ("NORMAL", False, True, None),
        ("NORMAL", True, False, None),
        ("NORMAL", False, False, None),
        ("READ_ONLY", True, True, Failures.READ_ONLY),
        ("READ_ONLY", False, True, Failures.READ_ONLY),
        ("READ_ONLY", True, False, Failures.READ_ONLY),
        ("READ_ONLY", False, False, Failures.READ_ONLY),
        ("MIRROR", True, True, None),
        ("MIRROR", False, True, Failures.MIRROR_ONLY),
        ("MIRROR", True, False, Failures.MIRROR_MISCONFIGURED),
        ("MIRROR", False, False, Failures.MIRROR_MISCONFIGURED),
    ],
)
def test_repository_states(
    state,
    use_robot,
    create_mirror,
    expected_failure,
    pusher,
    puller,
    basic_images,
    liveserver_session,
    api_caller,
    app_reloader,
):
    """
    Verify the push behavior of the Repository dependent upon its state.
    """
    namespace = "devtable"
    repo = "staterepo"
    tag = "latest"
    credentials = ("devtable", "password")
    robot = "dtrobot"
    robot_full_name = "%s+%s" % (namespace, robot)

    # Create repository
    pusher.push(liveserver_session, namespace, repo, tag, basic_images, credentials=credentials)

    # Login with API Caller
    api_caller.conduct_auth(*credentials)

    # When testing the Robot, assume the robot existed and had the correct permissions *before*
    # mirroring was configured.
    if use_robot:
        url = "/api/v1/repository/%s/%s/permissions/user/%s" % (namespace, repo, robot_full_name)
        data = json.dumps({"role": "write"})
        resp = api_caller.put(url, data=data, headers={"content-type": "application/json"})
        assert resp

    if create_mirror:
        params = {
            "is_enabled": True,
            "external_reference": "quay.io/foo/bar",
            "external_registry_username": "fakeusername",
            "external_registry_password": "fakepassword",
            "sync_interval": 1000,
            "sync_start_date": "2020-01-01T00:00:00Z",
            "root_rule": {"rule_kind": "tag_glob_csv", "rule_value": ["latest", "1.3*", "foo"]},
            "robot_username": robot_full_name,
            "external_registry_config": {
                "verify_tls": True,
                "proxy": {
                    "https_proxy": "https://proxy.example.net",
                    "http_proxy": "http://insecure.proxy.com",
                    "no_proxy": "local.lan.com",
                },
            },
        }

        url = "/api/v1/repository/%s/%s/mirror" % (namespace, repo)
        data = json.dumps(params)
        headers = {"Content-Type": "application/json"}
        resp = api_caller.post(url, data=data, headers=headers)
        assert resp  # Mirror was created successfully

    # Set the state of the Repository
    url = "/api/v1/repository/%s/%s/changestate" % (namespace, repo)
    data = json.dumps({"state": state})
    resp = api_caller.put(url, data=data, headers={"content-type": "application/json"})
    assert resp  # State was changed successfully

    # If testing the registry as the Robot user, use the Robot's credentials for all proceeding
    # API Calls
    if use_robot:
        resp = api_caller.get("/api/v1/user/robots/%s" % robot)
        data = resp.json()
        assert resp  # Robot credentials fetched successfully
        credentials = (data["name"], data["token"])

    # Verify pulls/reads still work
    puller.pull(liveserver_session, namespace, repo, tag, basic_images, credentials=credentials)

    # Should not be able to delete a robot attached to a mirror
    resp = api_caller.delete("/api/v1/user/robots/%s" % robot)
    assert resp.status_code == 400

    # Verify that the Repository.state determines whether pushes/changes are allowed
    options = ProtocolOptions()
    options.skip_head_checks = True
    pusher.push(
        liveserver_session,
        namespace,
        repo,
        tag,
        basic_images,
        credentials=credentials,
        expected_failure=expected_failure,
        options=options,
    )


def test_readonly_push_pull(
    pusher,
    puller,
    basic_images,
    different_images,
    liveserver_session,
    app_reloader,
    api_caller,
    liveserver,
    registry_server_executor,
):
    """ Test: Basic push an image to a new repository, followed by changing the system to readonly
            and then attempting a pull and a push.
  """
    credentials = ("devtable", "password")

    # Push a new repository.
    pusher.push(
        liveserver_session, "devtable", "newrepo", "latest", basic_images, credentials=credentials
    )

    # Change to read-only mode.
    with ConfigChange(
        "REGISTRY_STATE", "readonly", registry_server_executor.on(liveserver), liveserver
    ):
        # Pull the repository to verify.
        puller.pull(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
        )

        # Attempt to push to the repository, which should fail.
        pusher.push(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            different_images,
            credentials=credentials,
            expected_failure=Failures.READONLY_REGISTRY,
        )

        # Pull again to verify nothing has changed.
        puller.pull(
            liveserver_session,
            "devtable",
            "newrepo",
            "latest",
            basic_images,
            credentials=credentials,
        )


def test_malformed_schema2_config(v22_protocol, basic_images, liveserver_session, app_reloader):
    """
    Test: Attempt to push a manifest pointing to a config JSON that is missing a required
    key.
    """
    options = ProtocolOptions()
    options.with_broken_manifest_config = True

    credentials = ("devtable", "password")

    # Attempt to push a new repository. Should raise a 400.
    v22_protocol.push(
        liveserver_session,
        "devtable",
        "newrepo",
        "latest",
        basic_images,
        credentials=credentials,
        options=options,
        expected_failure=Failures.INVALID_MANIFEST,
    )
