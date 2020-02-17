from data import model

from test.fixtures import *


NO_ACCESS_USER = "freshuser"
READ_ACCESS_USER = "reader"
ADMIN_ACCESS_USER = "devtable"
PUBLIC_USER = "public"
RANDOM_USER = "randomuser"
OUTSIDE_ORG_USER = "outsideorg"

ADMIN_ROBOT_USER = "devtable+dtrobot"

ORGANIZATION = "buynlarge"

SIMPLE_REPO = "simple"
PUBLIC_REPO = "publicrepo"
RANDOM_REPO = "randomrepo"

OUTSIDE_ORG_REPO = "coolrepo"

ORG_REPO = "orgrepo"
ANOTHER_ORG_REPO = "anotherorgrepo"

# Note: The shared repo has devtable as admin, public as a writer and reader as a reader.
SHARED_REPO = "shared"


def assertDoesNotHaveRepo(username, name):
    repos = list(model.repository.get_visible_repositories(username))
    names = [repo.name for repo in repos]
    assert not name in names


def assertHasRepo(username, name):
    repos = list(model.repository.get_visible_repositories(username))
    names = [repo.name for repo in repos]
    assert name in names


def test_noaccess(initialized_db):
    repos = list(model.repository.get_visible_repositories(NO_ACCESS_USER))
    names = [repo.name for repo in repos]
    assert not names

    # Try retrieving public repos now.
    repos = list(model.repository.get_visible_repositories(NO_ACCESS_USER, include_public=True))
    names = [repo.name for repo in repos]
    assert PUBLIC_REPO in names


def test_public(initialized_db):
    assertHasRepo(PUBLIC_USER, PUBLIC_REPO)
    assertHasRepo(PUBLIC_USER, SHARED_REPO)

    assertDoesNotHaveRepo(PUBLIC_USER, SIMPLE_REPO)
    assertDoesNotHaveRepo(PUBLIC_USER, RANDOM_REPO)
    assertDoesNotHaveRepo(PUBLIC_USER, OUTSIDE_ORG_REPO)


def test_reader(initialized_db):
    assertHasRepo(READ_ACCESS_USER, SHARED_REPO)
    assertHasRepo(READ_ACCESS_USER, ORG_REPO)

    assertDoesNotHaveRepo(READ_ACCESS_USER, SIMPLE_REPO)
    assertDoesNotHaveRepo(READ_ACCESS_USER, RANDOM_REPO)
    assertDoesNotHaveRepo(READ_ACCESS_USER, OUTSIDE_ORG_REPO)
    assertDoesNotHaveRepo(READ_ACCESS_USER, PUBLIC_REPO)


def test_random(initialized_db):
    assertHasRepo(RANDOM_USER, RANDOM_REPO)

    assertDoesNotHaveRepo(RANDOM_USER, SIMPLE_REPO)
    assertDoesNotHaveRepo(RANDOM_USER, SHARED_REPO)
    assertDoesNotHaveRepo(RANDOM_USER, ORG_REPO)
    assertDoesNotHaveRepo(RANDOM_USER, ANOTHER_ORG_REPO)
    assertDoesNotHaveRepo(RANDOM_USER, PUBLIC_REPO)


def test_admin(initialized_db):
    assertHasRepo(ADMIN_ACCESS_USER, SIMPLE_REPO)
    assertHasRepo(ADMIN_ACCESS_USER, SHARED_REPO)

    assertHasRepo(ADMIN_ACCESS_USER, ORG_REPO)
    assertHasRepo(ADMIN_ACCESS_USER, ANOTHER_ORG_REPO)

    assertDoesNotHaveRepo(ADMIN_ACCESS_USER, OUTSIDE_ORG_REPO)
