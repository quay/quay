from unittest.mock import MagicMock, patch

import pytest

from test.fixtures import *
from workers.spamdetectionworker import (
    BATCH_SIZE,
    MIN_CONFIDENCE,
    SLEEP_BETWEEN_BATCHES,
    SpamDetectionWorker,
    create_gunicorn_worker,
)


def test_worker_initialization(initialized_db):
    worker = SpamDetectionWorker()
    assert len(worker._operations) == 1


@patch("workers.spamdetectionworker.SpamScanner")
@patch("workers.spamdetectionworker.ScanConfig")
def test_worker_scan_creates_scanner(mock_scan_config, mock_spam_scanner, initialized_db):
    mock_config_instance = MagicMock()
    mock_scan_config.return_value = mock_config_instance

    mock_scanner_instance = MagicMock()
    mock_spam_scanner.return_value = mock_scanner_instance

    worker = SpamDetectionWorker()
    worker._scan()

    mock_scan_config.assert_called_once()
    mock_spam_scanner.assert_called_once_with(mock_config_instance)
    mock_scanner_instance.scan.assert_called_once()


@patch("workers.spamdetectionworker.SpamScanner")
@patch("workers.spamdetectionworker.ScanConfig")
def test_worker_scan_config_values(mock_scan_config, mock_spam_scanner, initialized_db):
    mock_scanner_instance = MagicMock()
    mock_spam_scanner.return_value = mock_scanner_instance

    worker = SpamDetectionWorker()
    worker._scan()

    mock_scan_config.assert_called_once_with(
        batch_size=BATCH_SIZE,
        sleep_between_batches=SLEEP_BETWEEN_BATCHES,
        min_confidence_threshold=MIN_CONFIDENCE,
        dry_run=True,
    )


@patch("workers.spamdetectionworker.SpamScanner")
@patch("workers.spamdetectionworker.ScanConfig")
def test_create_gunicorn_worker(mock_scan_config, mock_spam_scanner, initialized_db):
    result = create_gunicorn_worker()
    assert result is not None
