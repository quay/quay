import logging

from calendar import timegm
from datetime import datetime
from uuid import uuid4

from peewee import IntegrityError, JOIN, fn
from data.model import (
    image,
    storage,
    db_transaction,
    DataModelException,
    _basequery,
    InvalidManifestException,
    TagAlreadyCreatedException,
    StaleTagException,
    config,
)
from data.database import (
    RepositoryTag,
    Repository,
    RepositoryState,
    Image,
    ImageStorage,
    Namespace,
    TagManifest,
    RepositoryNotification,
    Label,
    TagManifestLabel,
    get_epoch_timestamp,
    db_for_update,
    Manifest,
    ManifestLabel,
    ManifestBlob,
    ManifestLegacyImage,
    TagManifestToManifest,
    TagManifestLabelMap,
    TagToRepositoryTag,
    Tag,
    get_epoch_timestamp_ms,
)
from util.timedeltastring import convert_to_timedelta


logger = logging.getLogger(__name__)


def create_temporary_hidden_tag(repo, image_obj, expiration_s):
    """
    Create a tag with a defined timeline, that will not appear in the UI or CLI.

    Returns the name of the temporary tag or None on error.
    """
    now_ts = get_epoch_timestamp()
    expire_ts = now_ts + expiration_s
    tag_name = str(uuid4())

    # Ensure the repository is not marked for deletion.
    with db_transaction():
        current = Repository.get(id=repo)
        if current.state == RepositoryState.MARKED_FOR_DELETION:
            return None

        RepositoryTag.create(
            repository=repo,
            image=image_obj,
            name=tag_name,
            lifetime_start_ts=now_ts,
            lifetime_end_ts=expire_ts,
            hidden=True,
        )
        return tag_name


def lookup_unrecoverable_tags(repo):
    """
    Returns the tags  in a repository that are expired and past their time machine recovery period.
    """
    expired_clause = get_epoch_timestamp() - Namespace.removed_tag_expiration_s
    return (
        RepositoryTag.select()
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(RepositoryTag.repository == repo)
        .where(
            ~(RepositoryTag.lifetime_end_ts >> None),
            RepositoryTag.lifetime_end_ts <= expired_clause,
        )
    )
