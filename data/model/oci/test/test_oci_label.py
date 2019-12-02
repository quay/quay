import pytest

from playhouse.test_utils import assert_query_count

from data.database import Manifest, ManifestLabel
from data.model.oci.label import (
    create_manifest_label,
    list_manifest_labels,
    get_manifest_label,
    delete_manifest_label,
    DataModelException,
)

from test.fixtures import *


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
