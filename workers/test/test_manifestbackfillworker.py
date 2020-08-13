import pytest

from data import model, database
from image.shared.schemas import parse_manifest_from_bytes, ManifestException
from workers.manifestbackfillworker import ManifestBackfillWorker
from util.bytes import Bytes
from test.fixtures import *


def test_basic(initialized_db):
    worker = ManifestBackfillWorker()

    # Try with none to backfill.
    assert not worker._backfill_manifests()

    # Delete the sizes on some manifest rows.
    database.Manifest.update(layers_compressed_size=None).execute()

    # Try the backfill now.
    assert worker._backfill_manifests()

    # Ensure the rows were updated and correct.
    for manifest_row in database.Manifest.select():
        assert manifest_row.layers_compressed_size is not None

        manifest_bytes = Bytes.for_string_or_unicode(manifest_row.manifest_bytes)
        parsed = parse_manifest_from_bytes(
            manifest_bytes, manifest_row.media_type.name, validate=False
        )
        layers_compressed_size = parsed.layers_compressed_size or 0
        assert manifest_row.layers_compressed_size == layers_compressed_size
        assert manifest_row.config_media_type == parsed.config_media_type

    assert not worker._backfill_manifests()
