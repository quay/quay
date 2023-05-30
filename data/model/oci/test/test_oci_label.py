from test.fixtures import *

import pytest
from playhouse.test_utils import assert_query_count

from data.database import Manifest, ManifestLabel, Tag
from data.model import TagImmutableException
from data.model.oci.label import (
    DataModelException,
    create_manifest_label,
    delete_manifest_label,
    get_manifest_label,
    list_manifest_labels,
)
from data.model.oci.tag import get_tag, set_tag_immmutable


@pytest.mark.parametrize(
    "key, value, source_type, expected_error",
    [
        ("foo", "bar", "manifest", None),
        pytest.param("..foo", "bar", "manifest", None, id="invalid key on manifest"),
        pytest.param("..foo", "bar", "api", "is invalid", id="invalid key on api"),
    ],
)
def test_create_manifest_label(key, value, source_type, expected_error, initialized_db):
    manifest = Manifest.get()

    if expected_error:
        with pytest.raises(DataModelException) as ex:
            create_manifest_label(manifest, key, value, source_type)

        assert ex.match(expected_error)
        return

    label = create_manifest_label(manifest, key, value, source_type)
    labels = [
        ml.label_id for ml in ManifestLabel.select().where(ManifestLabel.manifest == manifest)
    ]
    assert label.id in labels

    with assert_query_count(1):
        assert label in list_manifest_labels(manifest)

    assert label not in list_manifest_labels(manifest, "someprefix")
    assert label in list_manifest_labels(manifest, key[0:2])

    with assert_query_count(1):
        assert get_manifest_label(label.uuid, manifest) == label

def test_create_manifest_label_with_immutable_tags(initialized_db):
    tag = Tag.get()
    repo = tag.repository

    assert tag.lifetime_end_ms is None

    with assert_query_count(2):
        assert set_tag_immmutable(repo, tag.name) == tag

    immutable_tag = get_tag(repo, tag.name)

    assert immutable_tag
    assert immutable_tag.manifest
    
    manifest = immutable_tag.manifest

    with pytest.raises(TagImmutableException):
        label = create_manifest_label(manifest, "foo", "bar", "manifest", raise_on_error=True)

def test_list_manifest_labels(initialized_db):
    manifest = Manifest.get()

    label1 = create_manifest_label(manifest, "foo", "1", "manifest")
    label2 = create_manifest_label(manifest, "bar", "2", "api")
    label3 = create_manifest_label(manifest, "baz", "3", "internal")

    assert label1 in list_manifest_labels(manifest)
    assert label2 in list_manifest_labels(manifest)
    assert label3 in list_manifest_labels(manifest)

    other_manifest = Manifest.select().where(Manifest.id != manifest.id).get()
    assert label1 not in list_manifest_labels(other_manifest)
    assert label2 not in list_manifest_labels(other_manifest)
    assert label3 not in list_manifest_labels(other_manifest)


def test_get_manifest_label(initialized_db):
    found = False
    for manifest_label in ManifestLabel.select():
        assert (
            get_manifest_label(manifest_label.label.uuid, manifest_label.manifest)
            == manifest_label.label
        )
        assert manifest_label.label in list_manifest_labels(manifest_label.manifest)
        found = True

    assert found


def test_delete_manifest_label(initialized_db):
    found = False
    for manifest_label in list(ManifestLabel.select()):
        assert (
            get_manifest_label(manifest_label.label.uuid, manifest_label.manifest)
            == manifest_label.label
        )
        assert manifest_label.label in list_manifest_labels(manifest_label.manifest)

        if manifest_label.label.source_type.mutable:
            assert delete_manifest_label(manifest_label.label.uuid, manifest_label.manifest)
            assert manifest_label.label not in list_manifest_labels(manifest_label.manifest)
            assert get_manifest_label(manifest_label.label.uuid, manifest_label.manifest) is None
        else:
            with pytest.raises(DataModelException):
                delete_manifest_label(manifest_label.label.uuid, manifest_label.manifest)

        found = True

    assert found

def test_delete_manifest_label_with_immutable_tags(initialized_db):
    tag = Tag.get()
    repo = tag.repository

    assert tag.lifetime_end_ms is None

    label = create_manifest_label(tag.manifest, "foo", "1", "manifest")

    assert label is not None

    assert set_tag_immmutable(repo, tag.name) == tag

    immutable_tag = get_tag(repo, tag.name)

    assert immutable_tag
    assert immutable_tag.manifest
    
    with pytest.raises(TagImmutableException):
        delete_manifest_label(label.uuid, immutable_tag.manifest, raise_on_error=True)