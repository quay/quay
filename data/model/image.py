import logging
import hashlib
import json

from collections import defaultdict
from datetime import datetime
import dateutil.parser

from peewee import JOIN, IntegrityError, fn

from data.model import (
    DataModelException,
    db_transaction,
    _basequery,
    storage,
    InvalidImageException,
)
from data.database import (
    Image,
    Repository,
    ImageStoragePlacement,
    Namespace,
    ImageStorage,
    ImageStorageLocation,
    RepositoryPermission,
    ImageStorageTransformation,
    User,
)

logger = logging.getLogger(__name__)


def _namespace_id_for_username(username):
    try:
        return User.get(username=username).id
    except User.DoesNotExist:
        return None


def get_image_with_storage(docker_image_id, storage_uuid):
    """
    Returns the image with the given docker image ID and storage uuid or None if none.
    """
    try:
        return (
            Image.select(Image, ImageStorage)
            .join(ImageStorage)
            .where(Image.docker_image_id == docker_image_id, ImageStorage.uuid == storage_uuid)
            .get()
        )
    except Image.DoesNotExist:
        return None


def get_parent_images(namespace_name, repository_name, image_obj):
    """
    Returns a list of parent Image objects starting with the most recent parent and ending with the
    base layer.

    The images in this query will include the storage.
    """
    parents = image_obj.ancestors

    # Ancestors are in the format /<root>/<intermediate>/.../<parent>/, with each path section
    # containing the database Id of the image row.
    parent_db_ids = parents.strip("/").split("/")
    if parent_db_ids == [""]:
        return []

    def filter_to_parents(query):
        return query.where(Image.id << parent_db_ids)

    parents = _get_repository_images_and_storages(
        namespace_name, repository_name, filter_to_parents
    )
    id_to_image = {str(image.id): image for image in parents}
    try:
        return [id_to_image[parent_id] for parent_id in reversed(parent_db_ids)]
    except KeyError as ke:
        logger.exception("Could not find an expected parent image for image %s", image_obj.id)
        raise DataModelException("Unknown parent image")


def get_placements_for_images(images):
    """
    Returns the placements for the given images, as a map from image storage ID to placements.
    """
    if not images:
        return {}

    query = (
        ImageStoragePlacement.select(ImageStoragePlacement, ImageStorageLocation, ImageStorage)
        .join(ImageStorageLocation)
        .switch(ImageStoragePlacement)
        .join(ImageStorage)
        .where(ImageStorage.id << [image.storage_id for image in images])
    )

    placement_map = defaultdict(list)
    for placement in query:
        placement_map[placement.storage.id].append(placement)

    return dict(placement_map)


def get_image_and_placements(namespace_name, repo_name, docker_image_id):
    """
    Returns the repo image (with a storage object) and storage placements for the image or (None,
    None) if non found.
    """
    repo_image = get_repo_image_and_storage(namespace_name, repo_name, docker_image_id)
    if repo_image is None:
        return (None, None)

    query = (
        ImageStoragePlacement.select(ImageStoragePlacement, ImageStorageLocation)
        .join(ImageStorageLocation)
        .switch(ImageStoragePlacement)
        .join(ImageStorage)
        .where(ImageStorage.id == repo_image.storage_id)
    )

    return repo_image, list(query)


def get_repo_image(namespace_name, repository_name, docker_image_id):
    """
    Returns the repository image with the given Docker image ID or None if none.

    Does not include the storage object.
    """

    def limit_to_image_id(query):
        return query.where(Image.docker_image_id == docker_image_id).limit(1)

    query = _get_repository_images(namespace_name, repository_name, limit_to_image_id)
    try:
        return query.get()
    except Image.DoesNotExist:
        return None


def get_repo_image_and_storage(namespace_name, repository_name, docker_image_id):
    """
    Returns the repository image with the given Docker image ID or None if none.

    Includes the storage object.
    """

    def limit_to_image_id(query):
        return query.where(Image.docker_image_id == docker_image_id)

    images = _get_repository_images_and_storages(namespace_name, repository_name, limit_to_image_id)
    if not images:
        return None

    return images[0]


def get_image_by_id(namespace_name, repository_name, docker_image_id):
    """
    Returns the repository image with the given Docker image ID or raises if not found.

    Includes the storage object.
    """
    image = get_repo_image_and_storage(namespace_name, repository_name, docker_image_id)
    if not image:
        raise InvalidImageException(
            "Unable to find image '%s' for repo '%s/%s'"
            % (docker_image_id, namespace_name, repository_name)
        )
    return image


def _get_repository_images_and_storages(namespace_name, repository_name, query_modifier):
    query = (
        Image.select(Image, ImageStorage)
        .join(ImageStorage)
        .switch(Image)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Repository.name == repository_name, Namespace.username == namespace_name)
    )

    query = query_modifier(query)
    return query


def _get_repository_images(namespace_name, repository_name, query_modifier):
    query = (
        Image.select()
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Repository.name == repository_name, Namespace.username == namespace_name)
    )

    query = query_modifier(query)
    return query


def lookup_repository_images(repo, docker_image_ids):
    return (
        Image.select(Image, ImageStorage)
        .join(ImageStorage)
        .where(Image.repository == repo, Image.docker_image_id << docker_image_ids)
    )


def get_repository_images_without_placements(repo_obj, with_ancestor=None):
    query = Image.select(Image, ImageStorage).join(ImageStorage).where(Image.repository == repo_obj)

    if with_ancestor:
        ancestors_string = "%s%s/" % (with_ancestor.ancestors, with_ancestor.id)
        query = query.where(
            (Image.ancestors ** (ancestors_string + "%")) | (Image.id == with_ancestor.id)
        )

    return query


def get_repository_images(namespace_name, repository_name):
    """
    Returns all the repository images in the repository.

    Does not include storage objects.
    """
    return _get_repository_images(namespace_name, repository_name, lambda q: q)


def __translate_ancestry(old_ancestry, translations, repo_obj, username, preferred_location):
    if old_ancestry == "/":
        return "/"

    def translate_id(old_id, docker_image_id):
        logger.debug("Translating id: %s", old_id)
        if old_id not in translations:
            image_in_repo = find_create_or_link_image(
                docker_image_id, repo_obj, username, translations, preferred_location
            )
            translations[old_id] = image_in_repo.id
        return translations[old_id]

    # Select all the ancestor Docker IDs in a single query.
    old_ids = [int(id_str) for id_str in old_ancestry.split("/")[1:-1]]
    query = Image.select(Image.id, Image.docker_image_id).where(Image.id << old_ids)
    old_images = {i.id: i.docker_image_id for i in query}

    # Translate the old images into new ones.
    new_ids = [str(translate_id(old_id, old_images[old_id])) for old_id in old_ids]
    return "/%s/" % "/".join(new_ids)


def _find_or_link_image(existing_image, repo_obj, username, translations, preferred_location):
    with db_transaction():
        # Check for an existing image, under the transaction, to make sure it doesn't already exist.
        repo_image = get_repo_image(
            repo_obj.namespace_user.username, repo_obj.name, existing_image.docker_image_id
        )
        if repo_image:
            return repo_image

        # Make sure the existing base image still exists.
        try:
            to_copy = Image.select().join(ImageStorage).where(Image.id == existing_image.id).get()

            msg = "Linking image to existing storage with docker id: %s and uuid: %s"
            logger.debug(msg, existing_image.docker_image_id, to_copy.storage.uuid)

            new_image_ancestry = __translate_ancestry(
                to_copy.ancestors, translations, repo_obj, username, preferred_location
            )

            copied_storage = to_copy.storage

            translated_parent_id = None
            if new_image_ancestry != "/":
                translated_parent_id = int(new_image_ancestry.split("/")[-2])

            new_image = Image.create(
                docker_image_id=existing_image.docker_image_id,
                repository=repo_obj,
                storage=copied_storage,
                ancestors=new_image_ancestry,
                command=existing_image.command,
                created=existing_image.created,
                comment=existing_image.comment,
                v1_json_metadata=existing_image.v1_json_metadata,
                aggregate_size=existing_image.aggregate_size,
                parent=translated_parent_id,
                v1_checksum=existing_image.v1_checksum,
            )

            logger.debug("Storing translation %s -> %s", existing_image.id, new_image.id)
            translations[existing_image.id] = new_image.id
            return new_image
        except Image.DoesNotExist:
            return None


def find_create_or_link_image(
    docker_image_id, repo_obj, username, translations, preferred_location
):

    # First check for the image existing in the repository. If found, we simply return it.
    repo_image = get_repo_image(repo_obj.namespace_user.username, repo_obj.name, docker_image_id)
    if repo_image:
        return repo_image

    # We next check to see if there is an existing storage the new image can link to.
    existing_image_query = (
        Image.select(Image, ImageStorage)
        .distinct()
        .join(ImageStorage)
        .switch(Image)
        .join(Repository)
        .join(RepositoryPermission, JOIN.LEFT_OUTER)
        .switch(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Image.docker_image_id == docker_image_id)
    )

    existing_image_query = _basequery.filter_to_repos_for_user(
        existing_image_query, _namespace_id_for_username(username)
    )

    # If there is an existing image, we try to translate its ancestry and copy its storage.
    new_image = None
    try:
        logger.debug("Looking up existing image for ID: %s", docker_image_id)
        existing_image = existing_image_query.get()

        logger.debug("Existing image %s found for ID: %s", existing_image.id, docker_image_id)
        new_image = _find_or_link_image(
            existing_image, repo_obj, username, translations, preferred_location
        )
        if new_image:
            return new_image
    except Image.DoesNotExist:
        logger.debug("No existing image found for ID: %s", docker_image_id)

    # Otherwise, create a new storage directly.
    with db_transaction():
        # Final check for an existing image, under the transaction.
        repo_image = get_repo_image(
            repo_obj.namespace_user.username, repo_obj.name, docker_image_id
        )
        if repo_image:
            return repo_image

        logger.debug("Creating new storage for docker id: %s", docker_image_id)
        new_storage = storage.create_v1_storage(preferred_location)

        return Image.create(
            docker_image_id=docker_image_id, repository=repo_obj, storage=new_storage, ancestors="/"
        )


def set_image_metadata(
    docker_image_id,
    namespace_name,
    repository_name,
    created_date_str,
    comment,
    command,
    v1_json_metadata,
    parent=None,
):
    """
    Sets metadata that is specific to how a binary piece of storage fits into the layer tree.
    """
    with db_transaction():
        try:
            fetched = (
                Image.select(Image, ImageStorage)
                .join(Repository)
                .join(Namespace, on=(Repository.namespace_user == Namespace.id))
                .switch(Image)
                .join(ImageStorage)
                .where(
                    Repository.name == repository_name,
                    Namespace.username == namespace_name,
                    Image.docker_image_id == docker_image_id,
                )
                .get()
            )
        except Image.DoesNotExist:
            raise DataModelException("No image with specified id and repository")

        fetched.created = datetime.now()
        if created_date_str is not None:
            try:
                fetched.created = dateutil.parser.parse(created_date_str).replace(tzinfo=None)
            except:
                # parse raises different exceptions, so we cannot use a specific kind of handler here.
                pass

        # We cleanup any old checksum in case it's a retry after a fail
        fetched.v1_checksum = None
        fetched.comment = comment
        fetched.command = command
        fetched.v1_json_metadata = v1_json_metadata

        if parent:
            fetched.ancestors = "%s%s/" % (parent.ancestors, parent.id)
            fetched.parent = parent

        fetched.save()
        return fetched


def get_image(repo, docker_image_id):
    try:
        return (
            Image.select(Image, ImageStorage)
            .join(ImageStorage)
            .where(Image.docker_image_id == docker_image_id, Image.repository == repo)
            .get()
        )
    except Image.DoesNotExist:
        return None


def get_image_by_db_id(id):
    try:
        return Image.get(id=id)
    except Image.DoesNotExist:
        return None


def synthesize_v1_image(
    repo,
    image_storage_id,
    storage_image_size,
    docker_image_id,
    created_date_str,
    comment,
    command,
    v1_json_metadata,
    parent_image=None,
):
    """
    Find an existing image with this docker image id, and if none exists, write one with the
    specified metadata.
    """
    ancestors = "/"
    if parent_image is not None:
        ancestors = "{0}{1}/".format(parent_image.ancestors, parent_image.id)

    created = None
    if created_date_str is not None:
        try:
            created = dateutil.parser.parse(created_date_str).replace(tzinfo=None)
        except:
            # parse raises different exceptions, so we cannot use a specific kind of handler here.
            pass

    # Get the aggregate size for the image.
    aggregate_size = _basequery.calculate_image_aggregate_size(
        ancestors, storage_image_size, parent_image
    )

    try:
        return Image.create(
            docker_image_id=docker_image_id,
            ancestors=ancestors,
            comment=comment,
            command=command,
            v1_json_metadata=v1_json_metadata,
            created=created,
            storage=image_storage_id,
            repository=repo,
            parent=parent_image,
            aggregate_size=aggregate_size,
        )
    except IntegrityError:
        return Image.get(docker_image_id=docker_image_id, repository=repo)


def ensure_image_locations(*names):
    with db_transaction():
        locations = ImageStorageLocation.select().where(ImageStorageLocation.name << names)

        insert_names = list(names)

        for location in locations:
            insert_names.remove(location.name)

        if not insert_names:
            return

        data = [{"name": name} for name in insert_names]
        ImageStorageLocation.insert_many(data).execute()


def get_max_id_for_sec_scan():
    """
    Gets the maximum id for a clair sec scan.
    """
    return Image.select(fn.Max(Image.id)).scalar()


def get_min_id_for_sec_scan(version):
    """
    Gets the minimum id for a clair sec scan.
    """
    return Image.select(fn.Min(Image.id)).where(Image.security_indexed_engine < version).scalar()


def total_image_count():
    """
    Returns the total number of images in DB.
    """
    return Image.select().count()


def get_image_pk_field():
    """
    Returns the primary key for Image DB model.
    """
    return Image.id


def get_images_eligible_for_scan(clair_version):
    """
    Returns a query that gives all images eligible for a clair scan.
    """
    return get_image_with_storage_and_parent_base().where(
        Image.security_indexed_engine < clair_version
    )


def get_image_with_storage_and_parent_base():
    Parent = Image.alias()
    ParentImageStorage = ImageStorage.alias()

    return (
        Image.select(Image, ImageStorage, Parent, ParentImageStorage)
        .join(ImageStorage)
        .switch(Image)
        .join(Parent, JOIN.LEFT_OUTER, on=(Image.parent == Parent.id))
        .join(ParentImageStorage, JOIN.LEFT_OUTER, on=(ParentImageStorage.id == Parent.storage))
    )


def set_secscan_status(image, indexed, version):
    return (
        Image.update(security_indexed=indexed, security_indexed_engine=version)
        .where(Image.id == image.id)
        .where((Image.security_indexed_engine != version) | (Image.security_indexed != indexed))
        .execute()
    ) != 0
