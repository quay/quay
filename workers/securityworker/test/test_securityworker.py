from mock import patch, Mock

from test.fixtures import *
from workers.securityworker import index_images


def test_securityworker_realdb(initialized_db):
    mock_analyzer = Mock()
    assert index_images(1, mock_analyzer) is not None
    mock_analyzer.analyze_recursively.assert_called()
