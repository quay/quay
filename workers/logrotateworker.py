import logging
import json
import time

from datetime import datetime
from gzip import GzipFile
from tempfile import SpooledTemporaryFile

import features
from app import app, storage
from data.logs_model import logs_model
from data.userfiles import DelegateUserfiles
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from util.streamingjsonencoder import StreamingJSONEncoder
from util.timedeltastring import convert_to_timedelta
from workers.worker import Worker
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)

JSON_MIMETYPE = "application/json"
MIN_LOGS_PER_ROTATION = 5000
MEMORY_TEMPFILE_SIZE = 12 * 1024 * 1024

WORKER_FREQUENCY = app.config.get("ACTION_LOG_ROTATION_FREQUENCY", 60 * 60 * 12)
STALE_AFTER = convert_to_timedelta(app.config.get("ACTION_LOG_ROTATION_THRESHOLD", "30d"))
MINIMUM_LOGS_AGE_FOR_ARCHIVE = convert_to_timedelta(
    app.config.get("MINIMUM_LOGS_AGE_FOR_ARCHIVE", "7d")
)
SAVE_PATH = app.config.get("ACTION_LOG_ARCHIVE_PATH")
SAVE_LOCATION = app.config.get("ACTION_LOG_ARCHIVE_LOCATION")


class LogRotateWorker(Worker):
    """
    Worker used to rotate old logs out the database and into storage.
    """

    def __init__(self):
        super(LogRotateWorker, self).__init__()
        self.add_operation(self._archive_logs, WORKER_FREQUENCY)

    def _archive_logs(self):
        cutoff_date = datetime.now() - STALE_AFTER
        try:
            with GlobalLock("ACTION_LOG_ROTATION"):
                self._perform_archiving(cutoff_date)
        except LockNotAcquiredException:
            return

    def _perform_archiving(self, cutoff_date):
        assert datetime.now() - cutoff_date >= MINIMUM_LOGS_AGE_FOR_ARCHIVE

        archived_files = []
        save_location = SAVE_LOCATION
        if not save_location:
            # Pick the *same* save location for all instances. This is a fallback if
            # a location was not configured.
            save_location = storage.locations[0]

        log_archive = DelegateUserfiles(app, storage, save_location, SAVE_PATH)

        for log_rotation_context in logs_model.yield_log_rotation_context(
            cutoff_date, MIN_LOGS_PER_ROTATION
        ):
            with log_rotation_context as context:
                for logs, filename in context.yield_logs_batch():
                    formatted_logs = [log_dict(log) for log in logs]
                    logger.debug("Archiving logs rotation %s", filename)
                    _write_logs(filename, formatted_logs, log_archive)
                    logger.debug("Finished archiving logs to %s", filename)
                    archived_files.append(filename)

        return archived_files


def log_dict(log):
    """
    Pretty prints a LogEntry in JSON.
    """
    try:
        # The `metadata_json` text field is replaced by `metadata` object field
        # when the logs model is set to elasticsearch
        if hasattr(log, "metadata_json"):
            metadata_json = json.loads(str(log.metadata_json))
        elif hasattr(log, "metadata") and log.metadata:
            metadata_json = log.metadata.to_dict()
        else:
            metadata_json = {}
    except AttributeError:
        logger.exception(
            "Could not get metadata for log entry %s",
            log.id if hasattr(log, "id") else log.random_id,
        )
        metadata_json = {}
    except ValueError:
        # The results returned by querying Elasticsearch does not have
        # a top-level attribute `id` like when querying with Peewee.
        # `random_id` is a copy of the document's `_id`.
        logger.exception(
            "Could not parse metadata JSON for log entry %s",
            log.id if hasattr(log, "id") else log.random_id,
        )
        metadata_json = {"__raw": log.metadata_json}
    except TypeError:
        logger.exception(
            "Could not parse metadata JSON for log entry %s",
            log.id if hasattr(log, "id") else log.random_id,
        )
        metadata_json = {"__raw": log.metadata_json}

    return {
        "kind_id": log.kind_id,
        "account_id": log.account_id,
        "performer_id": log.performer_id,
        "repository_id": log.repository_id,
        "datetime": str(log.datetime),
        "ip": str(log.ip),
        "metadata_json": metadata_json,
    }


def _write_logs(filename, logs, log_archive):
    with SpooledTemporaryFile(MEMORY_TEMPFILE_SIZE) as tempfile:
        with GzipFile("temp_action_log_rotate", fileobj=tempfile, compresslevel=1) as zipstream:
            for chunk in StreamingJSONEncoder().iterencode(logs):
                zipstream.write(chunk.encode("utf-8"))

        tempfile.seek(0)
        log_archive.store_file(tempfile, JSON_MIMETYPE, content_encoding="gzip", file_id=filename)


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    feature_flag = (features.ACTION_LOG_ROTATION) or (not None in [SAVE_PATH, SAVE_LOCATION])
    worker = GunicornWorker(__name__, app, LogRotateWorker(), feature_flag)
    return worker


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.ACTION_LOG_ROTATION or None in [SAVE_PATH, SAVE_LOCATION]:
        logger.debug("Action log rotation worker not enabled; skipping")
        while True:
            time.sleep(100000)

    worker = LogRotateWorker()
    worker.start()


if __name__ == "__main__":
    main()
