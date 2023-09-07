import hashlib
from uuid import uuid4

from data.model.blob import get_blob_upload_by_uuid, initiate_upload
from test.fixtures import *


def test_blobupload_sha_state(initialized_db: None) -> None:
    bu = initiate_upload("randomuser", "randomrepo", str(uuid4()), "local_us", {})
    bu.sha_state.update(b"hello")
    bu.save()
    bu = get_blob_upload_by_uuid(bu.uuid)
    assert bu is not None
    assert bu.sha_state.hexdigest() == hashlib.sha256(b"hello").hexdigest()
