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


def _open_stream(formatter, tag, schema1_manifest, derived_storage_id, handlers, reporter):
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
        derived_storage_id,
        layers,
        tar_stream_getter_iterator,
        reporter=reporter,
    )

    for handler_fn in handlers:
        stream = wrap_with_handler(stream, handler_fn)

    return stream.read


def _sign_derived_storage(verb, derived_storage, queue_file):
    """
    Read from the queue file and sign the contents which are generated.

    This method runs in a separate process.
    """
    signature = None
    try:
        signature = signer.detached_sign(queue_file)
    except:
        logger.exception("Exception when signing %s deriving storage %s", verb, derived_storage)
        return

    # Setup the database (since this is a new process) and then disconnect immediately
    # once the operation completes.
    if not queue_file.raised_exception:
        with database.UseThenDisconnect(app.config):
            registry_model.set_derived_storage_signature(derived_storage, signer.name, signature)


def _write_derived_storage_to_storage(
    verb, derived_storage, queue_file, namespace, repository, tag_name
):
    """
    Read from the generated stream and write it back to the storage engine.

    This method runs in a separate process.
    """

    def handle_exception(ex):
        logger.debug(
            "Exception when building %s derived storage %s (%s/%s:%s): %s",
            verb,
            derived_storage,
            namespace,
            repository,
            tag_name,
            ex,
        )

        with database.UseThenDisconnect(app.config):
            registry_model.delete_derived_storage(derived_storage)

    queue_file.add_exception_handler(handle_exception)

    # Re-Initialize the storage engine because some may not respond well to forking (e.g. S3)
    store = Storage(app, config_provider=config_provider, ip_resolver=ip_resolver)

    try:
        store.stream_write(
            derived_storage.blob.placements, derived_storage.blob.storage_path, queue_file
        )
    except IOError as ex:
        logger.error(
            "Exception when writing %s derived storage %s (%s/%s:%s): %s",
            verb,
            derived_storage,
            namespace,
            repository,
            tag_name,
            ex,
        )

        with database.UseThenDisconnect(app.config):
            registry_model.delete_derived_storage(derived_storage)

    queue_file.close()


def _torrent_for_blob(blob, is_public):
    """
    Returns a response containing the torrent file contents for the given blob.

    May abort with an error if the state is not valid (e.g. non-public, non-user request).
    """
    # Make sure the storage has a size.
    if not blob.compressed_size:
        abort(404)

    # Lookup the torrent information for the storage.
    torrent_info = registry_model.get_torrent_info(blob)
    if torrent_info is None:
        abort(404)

    # Lookup the webseed path for the storage.
    webseed = storage.get_direct_download_url(
        blob.placements, blob.storage_path, expires_in=app.config["BITTORRENT_WEBSEED_LIFETIME"]
    )
    if webseed is None:
        # We cannot support webseeds for storages that cannot provide direct downloads.
        exact_abort(501, "Storage engine does not support seeding.")

    # Load the config for building torrents.
    torrent_config = TorrentConfiguration.from_app_config(instance_keys, app.config)

    # Build the filename for the torrent.
    if is_public:
        name = public_torrent_filename(blob.uuid)
    else:
        user = get_authenticated_user()
        if not user:
            abort(403)

        name = per_user_torrent_filename(torrent_config, user.uuid, blob.uuid)

    # Return the torrent file.
    torrent_file = make_torrent(
        torrent_config,
        name,
        webseed,
        blob.compressed_size,
        torrent_info.piece_length,
        torrent_info.pieces,
    )

    headers = {
        "Content-Type": "application/x-bittorrent",
        "Content-Disposition": "attachment; filename={0}.torrent".format(name),
    }

    return make_response(torrent_file, 200, headers)


def _torrent_repo_verb(repository, tag, manifest, verb, **kwargs):
    """
    Handles returning a torrent for the given verb on the given image and tag.
    """
    if not features.BITTORRENT:
        # Torrent feature is not enabled.
        abort(406)

    # Lookup an *existing* derived storage for the verb. If the verb's image storage doesn't exist,
    # we cannot create it here, so we 406.
    derived_storage = registry_model.lookup_derived_storage(
        manifest, verb, storage, varying_metadata={"tag": tag.name}, include_placements=True
    )
    if derived_storage is None:
        abort(406)

    # Return the torrent.
    torrent = _torrent_for_blob(
        derived_storage.blob, model.repository.is_repository_public(repository)
    )

    # Log the action.
    track_and_log(
        "repo_verb", wrap_repository(repository), tag=tag.name, verb=verb, torrent=True, **kwargs
    )
    return torrent


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

    # Find the derived storage for the verb.
    derived_storage = registry_model.lookup_derived_storage(
        manifest, verb, storage, varying_metadata={"tag": tag.name}
    )

    if derived_storage is None or derived_storage.blob.uploading:
        return make_response("", 202)

    # Check if we have a valid signer configured.
    if not signer.name:
        abort(404)

    # Lookup the signature for the verb.
    signature_value = registry_model.get_derived_storage_signature(derived_storage, signer.name)
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

    # Lookup/create the derived storage for the verb and repo manifest.
    if is_readonly:
        derived_storage = registry_model.lookup_derived_storage(
            manifest, verb, storage, varying_metadata={"tag": tag.name}, include_placements=True
        )
    else:
        derived_storage = registry_model.lookup_or_create_derived_storage(
            manifest,
            verb,
            storage.preferred_locations[0],
            storage,
            varying_metadata={"tag": tag.name},
            include_placements=True,
        )
        if derived_storage is None:
            logger.error("Could not create or lookup a derived storage for manifest %s", manifest)
            abort(400)

    if derived_storage is not None and not derived_storage.blob.uploading:
        logger.debug("Derived %s storage %s exists in storage", verb, derived_storage)
        is_head_request = request.method == "HEAD"

        if derived_storage.blob.compressed_size:
            image_pulled_bytes.labels("verbs").inc(derived_storage.blob.compressed_size)

        download_url = storage.get_direct_download_url(
            derived_storage.blob.placements, derived_storage.blob.storage_path, head=is_head_request
        )
        if download_url:
            logger.debug(
                "Redirecting to download URL for derived %s storage %s", verb, derived_storage
            )
            return redirect(download_url)

        # Close the database handle here for this process before we send the long download.
        database.close_db_filter(None)

        logger.debug("Sending cached derived %s storage %s", verb, derived_storage)
        return send_file(
            storage.stream_read_file(
                derived_storage.blob.placements, derived_storage.blob.storage_path
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
            registry_model.set_derived_storage_size(derived_storage, hasher.hashed_bytes)

    # Create a queue process to generate the data. The queue files will read from the process
    # and send the results to the client and storage.
    unique_id = (
        derived_storage.unique_id
        if derived_storage is not None
        else hashlib.sha256("%s:%s" % (verb, uuid.uuid4())).hexdigest()
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
        storage_args = (verb, derived_storage, storage_queue_file, namespace, repository, tag_name)
        QueueProcess.run_process(_write_derived_storage_to_storage, storage_args, finished=_cleanup)

        if sign and signer.name:
            signing_args = (verb, derived_storage, signing_queue_file)
            QueueProcess.run_process(_sign_derived_storage, signing_args, finished=_cleanup)

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
