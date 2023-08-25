from datetime import datetime, timedelta
from test.fixtures import *

from mock import patch

from util.morecollections import AttrDict
from workers.servicekeyworker.models_pre_oci import pre_oci_model as model
from workers.servicekeyworker.servicekeyworker import ServiceKeyWorker


def test_refresh_service_key(initialized_db):
    # Create a service key for testing.
    original_expiration = datetime.utcnow() + timedelta(minutes=10)
    test_key_kid = model.create_service_key_for_testing(original_expiration)
    assert model.get_service_key_expiration(test_key_kid)

    instance_keys = AttrDict(dict(local_key_id=test_key_kid, service_key_expiration=30))
    with patch("workers.servicekeyworker.servicekeyworker.instance_keys", instance_keys):
        worker = ServiceKeyWorker()
        worker._refresh_service_key()

    # Ensure the key's expiration was changed.
    assert model.get_service_key_expiration(test_key_kid) > original_expiration
