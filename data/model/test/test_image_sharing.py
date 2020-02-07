import pytest

from data import model

from storage.distributedstorage import DistributedStorage
from storage.fakestorage import FakeStorage
from test.fixtures import *

NO_ACCESS_USER = "freshuser"
READ_ACCESS_USER = "reader"
ADMIN_ACCESS_USER = "devtable"
PUBLIC_USER = "public"
RANDOM_USER = "randomuser"
OUTSIDE_ORG_USER = "outsideorg"

ADMIN_ROBOT_USER = "devtable+dtrobot"

ORGANIZATION = "buynlarge"

REPO = "devtable/simple"
PUBLIC_REPO = "public/publicrepo"
RANDOM_REPO = "randomuser/randomrepo"

OUTSIDE_ORG_REPO = "outsideorg/coolrepo"

ORG_REPO = "buynlarge/orgrepo"
ANOTHER_ORG_REPO = "buynlarge/anotherorgrepo"

# Note: The shared repo has devtable as admin, public as a writer and reader as a reader.
SHARED_REPO = "devtable/shared"


@pytest.fixture()
def storage(app):
    return DistributedStorage({"local_us": FakeStorage(None)}, preferred_locations=["local_us"])


def createStorage(storage, docker_image_id, repository=REPO, username=ADMIN_ACCESS_USER):
    repository_obj = model.repository.get_repository(
        repository.split("/")[0], repository.split("/")[1]
    )
    preferred = storage.preferred_locations[0]
    image = model.image.find_create_or_link_image(
        docker_image_id, repository_obj, username, {}, preferred
    )
    image.storage.uploading = False
    image.storage.save()
    return image.storage


def assertSameStorage(
    storage, docker_image_id, existing_storage, repository=REPO, username=ADMIN_ACCESS_USER
):
    new_storage = createStorage(storage, docker_image_id, repository, username)
    assert existing_storage.id == new_storage.id


def assertDifferentStorage(
    storage, docker_image_id, existing_storage, repository=REPO, username=ADMIN_ACCESS_USER
):
    new_storage = createStorage(storage, docker_image_id, repository, username)
    assert existing_storage.id != new_storage.id


def test_same_user(storage, initialized_db):
    """
    The same user creates two images, each which should be shared in the same repo.

    This is a sanity check.
    """

    # Create a reference to a new docker ID => new image.
    first_storage_id = createStorage(storage, "first-image")

    # Create a reference to the same docker ID => same image.
    assertSameStorage(storage, "first-image", first_storage_id)

    # Create a reference to another new docker ID => new image.
    second_storage_id = createStorage(storage, "second-image")

    # Create a reference to that same docker ID => same image.
    assertSameStorage(storage, "second-image", second_storage_id)

    # Make sure the images are different.
    assert first_storage_id != second_storage_id


def test_no_user_private_repo(storage, initialized_db):
    """
    If no user is specified (token case usually), then no sharing can occur on a private repo.
    """
    # Create a reference to a new docker ID => new image.
    first_storage = createStorage(storage, "the-image", username=None, repository=SHARED_REPO)

    # Create a areference to the same docker ID, but since no username => new image.
    assertDifferentStorage(
        storage, "the-image", first_storage, username=None, repository=RANDOM_REPO
    )


def test_no_user_public_repo(storage, initialized_db):
    """
    If no user is specified (token case usually), then no sharing can occur on a private repo except
    when the image is first public.
    """
    # Create a reference to a new docker ID => new image.
    first_storage = createStorage(storage, "the-image", username=None, repository=PUBLIC_REPO)

    # Create a areference to the same docker ID. Since no username, we'd expect different but the first image is public so => shaed image.
    assertSameStorage(storage, "the-image", first_storage, username=None, repository=RANDOM_REPO)


def test_different_user_same_repo(storage, initialized_db):
    """
    Two different users create the same image in the same repo.
    """

    # Create a reference to a new docker ID under the first user => new image.
    first_storage = createStorage(
        storage, "the-image", username=PUBLIC_USER, repository=SHARED_REPO
    )

    # Create a reference to the *same* docker ID under the second user => same image.
    assertSameStorage(
        storage, "the-image", first_storage, username=ADMIN_ACCESS_USER, repository=SHARED_REPO
    )


def test_different_repo_no_shared_access(storage, initialized_db):
    """
    Neither user has access to the other user's repository.
    """

    # Create a reference to a new docker ID under the first user => new image.
    first_storage_id = createStorage(
        storage, "the-image", username=RANDOM_USER, repository=RANDOM_REPO
    )

    # Create a reference to the *same* docker ID under the second user => new image.
    second_storage_id = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=REPO
    )

    # Verify that the users do not share storage.
    assert first_storage_id != second_storage_id


def test_public_than_private(storage, initialized_db):
    """
    An image is created publicly then used privately, so it should be shared.
    """

    # Create a reference to a new docker ID under the first user => new image.
    first_storage = createStorage(
        storage, "the-image", username=PUBLIC_USER, repository=PUBLIC_REPO
    )

    # Create a reference to the *same* docker ID under the second user => same image, since the first was public.
    assertSameStorage(
        storage, "the-image", first_storage, username=ADMIN_ACCESS_USER, repository=REPO
    )


def test_private_than_public(storage, initialized_db):
    """
    An image is created privately then used publicly, so it should *not* be shared.
    """

    # Create a reference to a new docker ID under the first user => new image.
    first_storage = createStorage(storage, "the-image", username=ADMIN_ACCESS_USER, repository=REPO)

    # Create a reference to the *same* docker ID under the second user => new image, since the first was private.
    assertDifferentStorage(
        storage, "the-image", first_storage, username=PUBLIC_USER, repository=PUBLIC_REPO
    )


def test_different_repo_with_access(storage, initialized_db):
    """
    An image is created in one repo (SHARED_REPO) which the user (PUBLIC_USER) has access to.

    Later, the image is created in another repo (PUBLIC_REPO) that the user also has access to. The
    image should be shared since the user has access.
    """
    # Create the image in the shared repo => new image.
    first_storage = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=SHARED_REPO
    )

    # Create the image in the other user's repo, but since the user (PUBLIC) still has access to the shared
    # repository, they should reuse the storage.
    assertSameStorage(
        storage, "the-image", first_storage, username=PUBLIC_USER, repository=PUBLIC_REPO
    )


def test_org_access(storage, initialized_db):
    """
    An image is accessible by being a member of the organization.
    """

    # Create the new image under the org's repo => new image.
    first_storage = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=ORG_REPO
    )

    # Create an image under the user's repo, but since the user has access to the organization => shared image.
    assertSameStorage(
        storage, "the-image", first_storage, username=ADMIN_ACCESS_USER, repository=REPO
    )

    # Ensure that the user's robot does not have access, since it is not on the permissions list for the repo.
    assertDifferentStorage(
        storage, "the-image", first_storage, username=ADMIN_ROBOT_USER, repository=SHARED_REPO
    )


def test_org_access_different_user(storage, initialized_db):
    """
    An image is accessible by being a member of the organization.
    """

    # Create the new image under the org's repo => new image.
    first_storage = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=ORG_REPO
    )

    # Create an image under a user's repo, but since the user has access to the organization => shared image.
    assertSameStorage(
        storage, "the-image", first_storage, username=PUBLIC_USER, repository=PUBLIC_REPO
    )

    # Also verify for reader.
    assertSameStorage(
        storage, "the-image", first_storage, username=READ_ACCESS_USER, repository=PUBLIC_REPO
    )


def test_org_no_access(storage, initialized_db):
    """
    An image is not accessible if not a member of the organization.
    """

    # Create the new image under the org's repo => new image.
    first_storage = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=ORG_REPO
    )

    # Create an image under a user's repo. Since the user is not a member of the organization => new image.
    assertDifferentStorage(
        storage, "the-image", first_storage, username=RANDOM_USER, repository=RANDOM_REPO
    )


def test_org_not_team_member_with_access(storage, initialized_db):
    """
    An image is accessible to a user specifically listed as having permission on the org repo.
    """

    # Create the new image under the org's repo => new image.
    first_storage = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=ORG_REPO
    )

    # Create an image under a user's repo. Since the user has read access on that repo, they can see the image => shared image.
    assertSameStorage(
        storage, "the-image", first_storage, username=OUTSIDE_ORG_USER, repository=OUTSIDE_ORG_REPO
    )


def test_org_not_team_member_with_no_access(storage, initialized_db):
    """
    A user that has access to one org repo but not another and is not a team member.
    """

    # Create the new image under the org's repo => new image.
    first_storage = createStorage(
        storage, "the-image", username=ADMIN_ACCESS_USER, repository=ANOTHER_ORG_REPO
    )

    # Create an image under a user's repo. The user doesn't have access to the repo (ANOTHER_ORG_REPO) so => new image.
    assertDifferentStorage(
        storage, "the-image", first_storage, username=OUTSIDE_ORG_USER, repository=OUTSIDE_ORG_REPO
    )


def test_no_link_to_uploading(storage, initialized_db):
    still_uploading = createStorage(storage, "an-image", repository=PUBLIC_REPO)
    still_uploading.uploading = True
    still_uploading.save()

    assertDifferentStorage(storage, "an-image", still_uploading)
