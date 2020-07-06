import hashlib
import json
import logging
import uuid

from functools import wraps

from flask import redirect, Blueprint, abort, send_file, make_response, request
from prometheus_client import Counter

import features

from app import app, signer, storage, config_provider, ip_resolver, instance_keys
from auth.auth_context import get_authenticated_user
from auth.decorators import process_auth
from auth.permissions import ReadRepositoryPermission
from data import database
from data import model
from data.registry_model import registry_model
from endpoints.decorators import (
    anon_protect,
    anon_allowed,
    route_show_if,
    parse_repository_name,
    check_region_blacklisted,
)
from endpoints.metrics import image_pulls, image_pulled_bytes
from endpoints.v2.blob import BLOB_DIGEST_ROUTE
from image.appc import AppCImageFormatter
from image.shared import ManifestException
from image.docker.squashed import SquashedDockerImageFormatter
from storage import Storage
from util.audit import track_and_log, wrap_repository
from util.http import exact_abort
from util.metrics.prometheus import timed_blueprint
from util.registry.filelike import wrap_with_handler
from util.registry.queuefile import QueueFile
from util.registry.queueprocess import QueueProcess
from util.registry.tarlayerformat import TarLayerFormatterReporter


logger = logging.getLogger(__name__)
verbs = timed_blueprint(Blueprint("verbs", __name__))


verb_stream_passes = Counter(
    "quay_verb_stream_passes_total",
    "number of passes over a tar stream used by verb requests",
    labelnames=["kind"],
)


LAYER_MIMETYPE = "binary/octet-stream"
QUEUE_FILE_TIMEOUT = 15  # seconds


class VerbReporter(TarLayerFormatterReporter):
    def __init__(self, kind):
        self.kind = kind

    def report_pass(self, pass_count):
        if pass_count:
            verb_stream_passes.labels(self.kind).inc(pass_count)


def _open_stream(formatter, tag, schema1_manifest, derived_image_id, handlers, reporter):
    """
    This method generates a stream of data which will be replicated and read from the queue files.

    This method runs in a separate process.
    """
    # For performance reasons, we load the full image list here, cache it, then disconnect from
    # the database.
    with database.UseThenDisconnect(app.config):
        layers = registry_model.list_parsed_manifest_layers(
            tag.repository, schema1_manifest, storage, include_placements=True
        )

    def image_stream_getter(store, blob):
        def get_stream_for_storage():
            current_image_stream = store.stream_read_file(blob.placements, blob.storage_path)
            logger.debug("Returning blob %s: %s", blob.digest, blob.storage_path)
            return current_image_stream

        return get_stream_for_storage

    def tar_stream_getter_iterator():
        # Re-Initialize the storage engine because some may not respond well to forking (e.g. S3)
        store = Storage(app, config_provider=config_provider, ip_resolver=ip_resolver)

        # Note: We reverse because we have to start at the leaf layer and move upward,
        # as per the spec for the formatters.
        for layer in reversed(layers):
            yield image_stream_getter(store, layer.blob)

    stream = formatter.build_stream(
        tag,
        schema1_manifest,
        derived_image_id,
        layers,
        tar_stream_getter_iterator,
        reporter=reporter,
    )

    for handler_fn in handlers:
        stream = wrap_with_handler(stream, handler_fn)

    return stream.read


def _sign_derived_image(verb, derived_image, queue_file):
    """
    Read from the queue file and sign the contents which are generated.

    This method runs in a separate process.
    """
    signature = None
    try:
        signature = signer.detached_sign(queue_file)
    except Exception as e:
        logger.exception(
            "Exception when signing %s deriving image %s: $s", verb, derived_image, str(e)
        )
        return

    # Setup the database (since this is a new process) and then disconnect immediately
    # once the operation completes.
    if not queue_file.raised_exception:
        with database.UseThenDisconnect(app.config):
            registry_model.set_derived_image_signature(derived_image, signer.name, signature)


def _write_derived_image_to_storage(
    verb, derived_image, queue_file, namespace, repository, tag_name
):
    """
    Read from the generated stream and write it back to the storage engine.

    This method runs in a separate process.
    """

    def handle_exception(ex):
        logger.debug(
            "Exception when building %s derived image %s (%s/%s:%s): %s",
            verb,
            derived_image,
            namespace,
            repository,
            tag_name,
            ex,
        )

        with database.UseThenDisconnect(app.config):
            registry_model.delete_derived_image(derived_image)

    queue_file.add_exception_handler(handle_exception)

    # Re-Initialize the storage engine because some may not respond well to forking (e.g. S3)
    store = Storage(app, config_provider=config_provider, ip_resolver=ip_resolver)

    try:
        store.stream_write(
            derived_image.blob.placements, derived_image.blob.storage_path, queue_file
        )
    except IOError as ex:
        logger.error(
            "Exception when writing %s derived image %s (%s/%s:%s): %s",
            verb,
            derived_image,
            namespace,
            repository,
            tag_name,
            ex,
        )

        with database.UseThenDisconnect(app.config):
            registry_model.delete_derived_image(derived_image)

    queue_file.close()


def _verify_repo_verb(_, namespace, repo_name, tag_name, verb, checker=None):
    permission = ReadRepositoryPermission(namespace, repo_name)
    repo = model.repository.get_repository(namespace, repo_name)
    repo_is_public = repo is not None and model.repository.is_repository_public(repo)
    if not permission.can() and not repo_is_public:
        logger.debug(
            "No permission to read repository %s/%s for user %s with verb %s",
            namespace,
            repo_name,
            get_authenticated_user(),
            verb,
        )
        abort(403)

    if repo is not None and repo.kind.name != "image":
        logger.debug(
            "Repository %s/%s for user %s is not an image repo",
            namespace,
            repo_name,
            get_authenticated_user(),
        )
        abort(405)

    # Make sure the repo's namespace isn't disabled.
    if not registry_model.is_namespace_enabled(namespace):
        abort(400)

    # Lookup the requested tag.
    repo_ref = registry_model.lookup_repository(namespace, repo_name)
    if repo_ref is None:
        abort(404)

    tag = registry_model.get_repo_tag(repo_ref, tag_name)
    if tag is None:
        logger.debug(
            "Tag %s does not exist in repository %s/%s for user %s",
            tag,
            namespace,
            repo_name,
            get_authenticated_user(),
        )
        abort(404)

    # Get its associated manifest.
    manifest = registry_model.get_manifest_for_tag(tag, backfill_if_necessary=True)
    if manifest is None:
        logger.debug("Could not get manifest on %s/%s:%s::%s", namespace, repo_name, tag.name, verb)
        abort(404)

    # Retrieve the schema1-compatible version of the manifest.
    try:
        schema1_manifest = registry_model.get_schema1_parsed_manifest(
            manifest, namespace, repo_name, tag.name, storage
        )
    except ManifestException:
        logger.exception(
            "Could not get manifest on %s/%s:%s::%s", namespace, repo_name, tag.name, verb
        )
        abort(400)

    if schema1_manifest is None:
        abort(404)

    # If there is a data checker, call it first.
    if checker is not None:
        if not checker(tag, schema1_manifest):
            logger.debug(
                "Check mismatch on %s/%s:%s, verb %s", namespace, repo_name, tag.name, verb
            )
            abort(404)

    # Preload the tag's repository information, so it gets cached.
    assert tag.repository.namespace_name
    assert tag.repository.name

    return tag, manifest, schema1_manifest


def _repo_verb_signature(namespace, repository, tag_name, verb, checker=None, **kwargs):
    # Verify that the tag exists and that we have access to it.
    tag, manifest, _ = _verify_repo_verb(storage, namespace, repository, tag_name, verb, checker)

    # Find the derived image storage for the verb.
    derived_image = registry_model.lookup_derived_image(
        manifest, verb, storage, varying_metadata={"tag": tag.name}
    )

    if derived_image is None or derived_image.blob.uploading:
        return make_response("", 202)

    # Check if we have a valid signer configured.
    if not signer.name:
        abort(404)

    # Lookup the signature for the verb.
    signature_value = registry_model.get_derived_image_signature(derived_image, signer.name)
    if signature_value is None:
        abort(404)

    # Return the signature.
    return make_response(signature_value)


class SimpleHasher(object):
    def __init__(self):
        self._current_offset = 0

    def update(self, buf):
        self._current_offset += len(buf)

    @property
    def hashed_bytes(self):
        return self._current_offset


@check_region_blacklisted()
def _repo_verb(
    namespace, repository, tag_name, verb, formatter, sign=False, checker=None, **kwargs
):
    # Verify that the image exists and that we have access to it.
    logger.debug(
        "Verifying repo verb %s for repository %s/%s with user %s with mimetype %s",
        verb,
        namespace,
        repository,
        get_authenticated_user(),
        request.accept_mimetypes.best,
    )
    tag, manifest, schema1_manifest = _verify_repo_verb(
        storage, namespace, repository, tag_name, verb, checker
    )

    # Load the repository for later.
    repo = model.repository.get_repository(namespace, repository)
    if repo is None:
        abort(404)

    # Check for torrent, which is no longer supported.
    if request.accept_mimetypes.best == "application/x-bittorrent":
        abort(406)

    # Log the action.
    track_and_log("repo_verb", wrap_repository(repo), tag=tag.name, verb=verb, **kwargs)

    is_readonly = app.config.get("REGISTRY_STATE", "normal") == "readonly"

    # Lookup/create the derived image for the verb and repo image.
    if is_readonly:
        derived_image = registry_model.lookup_derived_image(
            manifest, verb, storage, varying_metadata={"tag": tag.name}, include_placements=True
        )
    else:
        derived_image = registry_model.lookup_or_create_derived_image(
            manifest,
            verb,
            storage.preferred_locations[0],
            storage,
            varying_metadata={"tag": tag.name},
            include_placements=True,
        )
        if derived_image is None:
            logger.error("Could not create or lookup a derived image for manifest %s", manifest)
            abort(400)

    if derived_image is not None and not derived_image.blob.uploading:
        logger.debug("Derived %s image %s exists in storage", verb, derived_image)
        is_head_request = request.method == "HEAD"

        if derived_image.blob.compressed_size:
            image_pulled_bytes.labels("verbs").inc(derived_image.blob.compressed_size)

        download_url = storage.get_direct_download_url(
            derived_image.blob.placements, derived_image.blob.storage_path, head=is_head_request
        )
        if download_url:
            logger.debug("Redirecting to download URL for derived %s image %s", verb, derived_image)
            return redirect(download_url)

        # Close the database handle here for this process before we send the long download.
        database.close_db_filter(None)

        logger.debug("Sending cached derived %s image %s", verb, derived_image)
        return send_file(
            storage.stream_read_file(
                derived_image.blob.placements, derived_image.blob.storage_path
            ),
            mimetype=LAYER_MIMETYPE,
        )

    logger.debug("Building and returning derived %s image", verb)
    hasher = SimpleHasher()

    # Close the database connection before any process forking occurs. This is important because
    # the Postgres driver does not react kindly to forking, so we need to make sure it is closed
    # so that each process will get its own unique connection.
    database.close_db_filter(None)

    def _cleanup():
        # Close any existing DB connection once the process has exited.
        database.close_db_filter(None)

    def _store_metadata_and_cleanup():
        if is_readonly:
            return

        with database.UseThenDisconnect(app.config):
            registry_model.set_derived_image_size(derived_image, hasher.hashed_bytes)

    # Create a queue process to generate the data. The queue files will read from the process
    # and send the results to the client and storage.
    unique_id = (
        derived_image.unique_id
        if derived_image is not None
        else hashlib.sha256(("%s:%s" % (verb, uuid.uuid4())).encode("utf-8")).hexdigest()
    )
    handlers = [hasher.update]
    reporter = VerbReporter(verb)
    args = (formatter, tag, schema1_manifest, unique_id, handlers, reporter)
    queue_process = QueueProcess(
        _open_stream,
        8 * 1024,
        10 * 1024 * 1024,  # 8K/10M chunk/max
        args,
        finished=_store_metadata_and_cleanup,
    )

    client_queue_file = QueueFile(
        queue_process.create_queue(), "client", timeout=QUEUE_FILE_TIMEOUT
    )

    if not is_readonly:
        storage_queue_file = QueueFile(
            queue_process.create_queue(), "storage", timeout=QUEUE_FILE_TIMEOUT
        )

        # If signing is required, add a QueueFile for signing the image as we stream it out.
        signing_queue_file = None
        if sign and signer.name:
            signing_queue_file = QueueFile(
                queue_process.create_queue(), "signing", timeout=QUEUE_FILE_TIMEOUT
            )

    # Start building.
    queue_process.run()

    # Start the storage saving.
    if not is_readonly:
        storage_args = (verb, derived_image, storage_queue_file, namespace, repository, tag_name)
        QueueProcess.run_process(_write_derived_image_to_storage, storage_args, finished=_cleanup)

        if sign and signer.name:
            signing_args = (verb, derived_image, signing_queue_file)
            QueueProcess.run_process(_sign_derived_image, signing_args, finished=_cleanup)

    # Close the database handle here for this process before we send the long download.
    database.close_db_filter(None)

    # Return the client's data.
    return send_file(client_queue_file, mimetype=LAYER_MIMETYPE)


def os_arch_checker(os, arch):
    def checker(tag, manifest):
        try:
            image_json = json.loads(manifest.leaf_layer.raw_v1_metadata)
        except ValueError:
            logger.exception("Could not parse leaf layer JSON for manifest %s", manifest)
            return False
        except TypeError:
            logger.exception("Could not parse leaf layer JSON for manifest %s", manifest)
            return False

        # Verify the architecture and os.
        operating_system = image_json.get("os", "linux")
        if operating_system != os:
            return False

        architecture = image_json.get("architecture", "amd64")

        # Note: Some older Docker images have 'x86_64' rather than 'amd64'.
        # We allow the conversion here.
        if architecture == "x86_64" and operating_system == "linux":
            architecture = "amd64"

        if architecture != arch:
            return False

        return True

    return checker


def observe_route(protocol):
    """
    Decorates verb endpoints to record the image_pulls metric into Prometheus.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rv = func(*args, **kwargs)
            image_pulls.labels(protocol, "tag", rv.status_code)
            return rv

        return wrapper

    return decorator


@route_show_if(features.ACI_CONVERSION)
@anon_protect
@verbs.route("/aci/<server>/<namespace>/<repository>/<tag>/sig/<os>/<arch>/", methods=["GET"])
@verbs.route("/aci/<server>/<namespace>/<repository>/<tag>/aci.asc/<os>/<arch>/", methods=["GET"])
@observe_route("aci")
@process_auth
def get_aci_signature(server, namespace, repository, tag, os, arch):
    return _repo_verb_signature(
        namespace, repository, tag, "aci", checker=os_arch_checker(os, arch), os=os, arch=arch
    )


@route_show_if(features.ACI_CONVERSION)
@anon_protect
@verbs.route(
    "/aci/<server>/<namespace>/<repository>/<tag>/aci/<os>/<arch>/", methods=["GET", "HEAD"]
)
@observe_route("aci")
@process_auth
def get_aci_image(server, namespace, repository, tag, os, arch):
    return _repo_verb(
        namespace,
        repository,
        tag,
        "aci",
        AppCImageFormatter(),
        sign=True,
        checker=os_arch_checker(os, arch),
        os=os,
        arch=arch,
    )


@anon_protect
@verbs.route("/squash/<namespace>/<repository>/<tag>", methods=["GET"])
@observe_route("squash")
@process_auth
def get_squashed_tag(namespace, repository, tag):
    return _repo_verb(namespace, repository, tag, "squash", SquashedDockerImageFormatter())


@verbs.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)
