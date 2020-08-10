from auth.registry_jwt_auth import identity_from_bearer_token
from app import app as application, storage, instance_keys
from data.registry_model import registry_model
from endpoints.v2 import v2_bp
from util.secscan.blob import BlobURLRetriever

from test.fixtures import *


def test_generate_url(initialized_db):
    try:
        application.register_blueprint(v2_bp, url_prefix="/v2")
    except:
        # Already registered.
        pass

    repo_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = tag.manifest
    blobs = registry_model.get_manifest_local_blobs(manifest, storage)

    retriever = BlobURLRetriever(storage, instance_keys, application)
    headers = retriever.headers_for_download(repo_ref, blobs[0])

    identity, _ = identity_from_bearer_token(headers["Authorization"][0])
    assert len(identity.provides) == 1

    provide = list(identity.provides)[0]
    assert provide.role == "read"
    assert provide.name == "simple"
    assert provide.namespace == "devtable"
    assert provide.type == "repository"

    assert retriever.url_for_download(repo_ref, blobs[0]).startswith(
        "http://localhost:5000/v2/devtable/simple/blobs/"
    )
