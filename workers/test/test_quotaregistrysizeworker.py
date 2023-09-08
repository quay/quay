from test.fixtures import *
from unittest.mock import MagicMock, patch

from workers.quotaregistrysizeworker import QuotaRegistrySizeWorker


def test_registrysizeworker(initialized_db):
    with patch(
        "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
    ) as mock_calculate_registry_size:
        worker = QuotaRegistrySizeWorker()
        worker._calculate_registry_size()
        assert mock_calculate_registry_size.called
