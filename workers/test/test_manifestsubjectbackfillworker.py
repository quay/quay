import pytest

from data import database, model
from test.fixtures import *
from workers.manifestsubjectbackfillworker import ManifestSubjectBackfillWorker


def test_basic(initialized_db):
    worker = ManifestSubjectBackfillWorker()

    # By default new manifests are already backfilled (i.e subject. if any, are parsed at creation)
    assert not worker._backfill_manifest_subject()

    # Set manifests to be backfilled some manifests
    database.Manifest.update(subject_backfilled=False).execute()

    assert worker._backfill_manifest_subject()

    for manifest_row in database.Manifest.select():
        assert manifest_row.subject_backfilled is True

        if manifest_row.subject is not None:
            database.Manifest.select().where(
                database.Manifest.repository == manifest_row.repository,
                database.Manifest.digest == manifest_row.subject,
            ).get()

    assert not worker._backfill_manifest_subject()
