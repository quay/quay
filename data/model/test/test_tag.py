import pytest

from data.database import (
    RepositoryState,
    Image,
)

from test.fixtures import *


def test_create_temp_tag(initialized_db):
    repo = model.repository.get_repository("devtable", "simple")
    image = Image.get(repository=repo)
    assert model.tag.create_temporary_hidden_tag(repo, image, 10000000) is not None


def test_create_temp_tag_deleted_repo(initialized_db):
    repo = model.repository.get_repository("devtable", "simple")
    repo.state = RepositoryState.MARKED_FOR_DELETION
    repo.save()

    image = Image.get(repository=repo)
    assert model.tag.create_temporary_hidden_tag(repo, image, 10000000) is None
