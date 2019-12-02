import pytest

from collections import defaultdict
from data.model import image, repository
from playhouse.test_utils import assert_query_count

from test.fixtures import *


@pytest.fixture()
def images(initialized_db):
    images = image.get_repository_images("devtable", "simple")
    assert len(images)
    return images


def test_get_image_with_storage(images, initialized_db):
    for current in images:
        storage_uuid = current.storage.uuid

        with assert_query_count(1):
            retrieved = image.get_image_with_storage(current.docker_image_id, storage_uuid)
            assert retrieved.id == current.id
            assert retrieved.storage.uuid == storage_uuid


def test_get_parent_images(images, initialized_db):
    for current in images:
        if not len(current.ancestor_id_list()):
            continue

        with assert_query_count(1):
            parent_images = list(image.get_parent_images("devtable", "simple", current))

        assert len(parent_images) == len(current.ancestor_id_list())
        assert set(current.ancestor_id_list()) == {i.id for i in parent_images}

        for parent in parent_images:
            with assert_query_count(0):
                assert parent.storage.id


def test_get_image(images, initialized_db):
    for current in images:
        repo = current.repository

        with assert_query_count(1):
            found = image.get_image(repo, current.docker_image_id)

        assert found.id == current.id


def test_placements(images, initialized_db):
    with assert_query_count(1):
        placements_map = image.get_placements_for_images(images)

    for current in images:
        assert current.storage.id in placements_map

        with assert_query_count(2):
            expected_image, expected_placements = image.get_image_and_placements(
                "devtable", "simple", current.docker_image_id
            )

        assert expected_image.id == current.id
        assert len(expected_placements) == len(placements_map.get(current.storage.id))
        assert {p.id for p in expected_placements} == {
            p.id for p in placements_map.get(current.storage.id)
        }


def test_get_repo_image(images, initialized_db):
    for current in images:
        with assert_query_count(1):
            found = image.get_repo_image("devtable", "simple", current.docker_image_id)

        assert found.id == current.id
        with assert_query_count(1):
            assert found.storage.id


def test_get_repo_image_and_storage(images, initialized_db):
    for current in images:
        with assert_query_count(1):
            found = image.get_repo_image_and_storage("devtable", "simple", current.docker_image_id)

        assert found.id == current.id
        with assert_query_count(0):
            assert found.storage.id


def test_get_repository_images_without_placements(images, initialized_db):
    ancestors_map = defaultdict(list)
    for img in images:
        current = img.parent
        while current is not None:
            ancestors_map[current.id].append(img.id)
            current = current.parent

    for current in images:
        repo = current.repository

        with assert_query_count(1):
            found = list(
                image.get_repository_images_without_placements(repo, with_ancestor=current)
            )

        assert len(found) == len(ancestors_map[current.id]) + 1
        assert {i.id for i in found} == set(ancestors_map[current.id] + [current.id])
