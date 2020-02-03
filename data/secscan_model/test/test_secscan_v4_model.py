from peewee import fn

from data.secscan_model.secscan_v4_model import V4SecurityScanner
from data.database import Manifest, Repository

from test.fixtures import *

from app import app, instance_keys, storage


def test_perform_indexing_whitelist(initialized_db):
    app.config["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"] = ["devtable"]
    secscan = V4SecurityScanner(app, instance_keys, storage)

    next_token = secscan.perform_indexing()

    assert (
        Manifest.get_by_id(next_token.min_id - 1).repository.namespace_user.username == "devtable"
    )


def test_perform_indexing_no_whitelist(initialized_db):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    next_token = secscan.perform_indexing()

    assert next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1
