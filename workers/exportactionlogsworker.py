import logging
import os.path
import json
import time
import uuid

from datetime import datetime, timedelta
from io import BytesIO

from enum import Enum, unique

import features

from app import app, export_action_logs_queue, storage as app_storage, get_app_url, avatar
from endpoints.api import format_date
from data.logs_model import logs_model
from data.logs_model.interface import LogsIterationTimeout
from workers.queueworker import QueueWorker
from util.log import logfile_path
from util.useremails import send_logs_exported_email
from workers.gunicorn_worker import GunicornWorker


logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = app.config.get("EXPORT_ACTION_LOGS_WORKER_POLL_PERIOD", 60)

EXPORT_LOGS_STORAGE_PATH = app.config.get("EXPORT_ACTION_LOGS_STORAGE_PATH", "exportedactionlogs")
MAXIMUM_WORK_PERIOD_SECONDS = app.config.get(
    "EXPORT_ACTION_LOGS_MAXIMUM_SECONDS", 60 * 60
)  # 1 hour
MAXIMUM_QUERY_TIME_SECONDS = app.config.get("EXPORT_ACTION_LOGS_MAXIMUM_QUERY_TIME_SECONDS", 30)
EXPORTED_LOGS_EXPIRATION_SECONDS = app.config.get("EXPORT_ACTION_LOGS_SECONDS", 60 * 60)  # 1 hour


@unique
class ExportResult(Enum):
    # NOTE: Make sure to handle these in `logsexported.html` in `emails`
    INVALID_REQUEST = "invalidrequest"
    OPERATION_TIMEDOUT = "timedout"
    FAILED_EXPORT = "failed"
    SUCCESSFUL_EXPORT = "success"


class ExportActionLogsWorker(QueueWorker):
    """
    Worker which exports action logs for a namespace or a repository based on a queued request from
    the API.
    """

    def process_queue_item(self, job_details):
        return self._process_queue_item(job_details, app_storage)

    def _process_queue_item(self, job_details, storage):
        logger.info("Got export actions logs queue item: %s", job_details)

        # job_details block (as defined in the logs.py API endpoint):
        # {
        #  'export_id': export_id,
        #  'repository_id': repository.id or None,
        #  'namespace_id': namespace.id,
        #  'namespace_name': namespace.username,
        #  'repository_name': repository.name or None,
        #  'start_time': start_time,
        #  'end_time': end_time,
        #  'callback_url': callback_url or None,
        #  'callback_email': callback_email or None,
        # }
        export_id = job_details["export_id"]

        start_time = _parse_time(job_details["start_time"])
        end_time = _parse_time(job_details["end_time"])

        # Make sure the end time has the whole day.
        if start_time is None or end_time is None:
            self._report_results(job_details, ExportResult.INVALID_REQUEST)
            return

        end_time = end_time + timedelta(days=1) - timedelta(milliseconds=1)

        # Select the minimum and maximum IDs for the logs for the repository/namespace
        # over the time range.
        namespace_id = job_details["namespace_id"]
        repository_id = job_details["repository_id"]
        max_query_time = timedelta(seconds=MAXIMUM_QUERY_TIME_SECONDS)

        # Generate a file key so that if we return an API URL, it cannot simply be constructed from
        # just the export ID.
        file_key = str(uuid.uuid4())
        exported_filename = "%s-%s" % (export_id, file_key)

        # Start a chunked upload for the logs and stream them.
        upload_id, upload_metadata = storage.initiate_chunked_upload(storage.preferred_locations)
        export_storage_path = os.path.join(EXPORT_LOGS_STORAGE_PATH, exported_filename)
        logger.debug("Starting chunked upload to path `%s`", export_storage_path)

        # Start with a 'json' header that contains the opening bracket, as well as basic
        # information and the start of the `logs` array.
        details = {
            "start_time": format_date(start_time),
            "end_time": format_date(end_time),
            "namespace": job_details["namespace_name"],
            "repository": job_details["repository_name"],
        }

        prefix_data = """{
      "export_id": "%s",
      "details": %s,
      "logs": [
    """ % (
            export_id,
            json.dumps(details),
        )

        _, new_metadata, upload_error = storage.stream_upload_chunk(
            storage.preferred_locations,
            upload_id,
            0,
            -1,
            BytesIO(prefix_data.encode("utf-8")),
            upload_metadata,
        )
        uploaded_byte_count = len(prefix_data)
        if upload_error is not None:
            logger.error("Got an error when writing chunk for `%s`: %s", export_id, upload_error)
            storage.cancel_chunked_upload(storage.preferred_locations, upload_id, upload_metadata)
            self._report_results(job_details, ExportResult.FAILED_EXPORT)
            raise IOError(upload_error)

        upload_metadata = new_metadata
        logs_iterator = logs_model.yield_logs_for_export(
            start_time, end_time, repository_id, namespace_id, max_query_time
        )

        try:
            # Stream the logs to storage as chunks.
            new_metadata, uploaded_byte_count = self._stream_logs(
                upload_id, upload_metadata, uploaded_byte_count, logs_iterator, job_details, storage
            )
            if uploaded_byte_count is None:
                logger.error("Failed to upload streamed logs for `%s`", export_id)
                storage.cancel_chunked_upload(
                    storage.preferred_locations, upload_id, upload_metadata
                )
                self._report_results(job_details, ExportResult.FAILED_EXPORT)
                raise IOError("Export failed to upload")

            upload_metadata = new_metadata

            # Close the JSON block.
            suffix_data = """
        {"terminator": true}]
      }"""

            _, new_metadata, upload_error = storage.stream_upload_chunk(
                storage.preferred_locations,
                upload_id,
                0,
                -1,
                BytesIO(suffix_data.encode("utf-8")),
                upload_metadata,
            )
            if upload_error is not None:
                logger.error(
                    "Got an error when writing chunk for `%s`: %s", export_id, upload_error
                )
                storage.cancel_chunked_upload(
                    storage.preferred_locations, upload_id, upload_metadata
                )
                self._report_results(job_details, ExportResult.FAILED_EXPORT)
                raise IOError(upload_error)

            # Complete the upload.
            upload_metadata = new_metadata
            storage.complete_chunked_upload(
                storage.preferred_locations, upload_id, export_storage_path, upload_metadata
            )
        except:
            logger.exception("Exception when exporting logs for `%s`", export_id)
            storage.cancel_chunked_upload(storage.preferred_locations, upload_id, upload_metadata)
            self._report_results(job_details, ExportResult.FAILED_EXPORT)
            raise

        # Invoke the callbacks.
        export_url = storage.get_direct_download_url(
            storage.preferred_locations,
            export_storage_path,
            expires_in=EXPORTED_LOGS_EXPIRATION_SECONDS,
        )
        if export_url is None:
            export_url = "%s/exportedlogs/%s" % (get_app_url(), exported_filename)

        self._report_results(job_details, ExportResult.SUCCESSFUL_EXPORT, export_url)

    def _stream_logs(
        self, upload_id, upload_metadata, uploaded_byte_count, logs_iterator, job_details, storage
    ):
        export_id = job_details["export_id"]
        max_work_period = timedelta(seconds=MAXIMUM_WORK_PERIOD_SECONDS)
        batch_start_time = datetime.utcnow()

        try:
            for logs in logs_iterator:
                work_elapsed = datetime.utcnow() - batch_start_time
                if work_elapsed > max_work_period:
                    logger.error(
                        "Retrieval of logs `%s` timed out with time of `%s`",
                        export_id,
                        work_elapsed,
                    )
                    self._report_results(job_details, ExportResult.OPERATION_TIMEDOUT)
                    return None, None

                logs_data = ""
                if logs:
                    logs_data = (
                        ",".join([json.dumps(log.to_dict(avatar, False)) for log in logs]) + ","
                    )

                logs_data = logs_data.encode("utf-8")
                if logs_data:
                    _, new_metadata, upload_error = storage.stream_upload_chunk(
                        storage.preferred_locations,
                        upload_id,
                        0,
                        -1,
                        BytesIO(logs_data),
                        upload_metadata,
                    )

                    if upload_error is not None:
                        logger.error("Got an error when writing chunk: %s", upload_error)
                        return upload_metadata, None

                    upload_metadata = new_metadata
                    uploaded_byte_count += len(logs_data)
        except LogsIterationTimeout:
            logger.error("Retrieval of logs for export logs timed out at `%s`", work_elapsed)
            self._report_results(job_details, ExportResult.OPERATION_TIMEDOUT)
            return upload_metadata, None

        return upload_metadata, uploaded_byte_count

    def _report_results(self, job_details, result_status, exported_data_url=None):
        logger.debug(
            "Reporting result of `%s` for %s; %s", result_status, job_details, exported_data_url
        )

        if job_details.get("callback_url"):
            # Post the results to the callback URL.
            client = app.config["HTTPCLIENT"]
            result = client.post(
                job_details["callback_url"],
                json={
                    "export_id": job_details["export_id"],
                    "start_time": job_details["start_time"],
                    "end_time": job_details["end_time"],
                    "namespace": job_details["namespace_name"],
                    "repository": job_details["repository_name"],
                    "exported_data_url": exported_data_url,
                    "status": result_status.value,
                },
            )

            if result.status_code != 200:
                logger.error(
                    "Got `%s` status code for callback URL `%s` for export `%s`",
                    result.status_code,
                    job_details["callback_url"],
                    job_details["export_id"],
                )
                raise Exception("Got non-200 for batch logs reporting; retrying later")

        if job_details.get("callback_email"):
            with app.app_context():
                send_logs_exported_email(
                    job_details["callback_email"],
                    job_details["export_id"],
                    result_status.value,
                    exported_data_url,
                    EXPORTED_LOGS_EXPIRATION_SECONDS,
                )


def _parse_time(specified_time):
    try:
        return datetime.strptime(specified_time + " UTC", "%m/%d/%Y %Z")
    except ValueError:
        return None


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    log_worker = ExportActionLogsWorker(
        export_action_logs_queue, poll_period_seconds=POLL_PERIOD_SECONDS
    )
    worker = GunicornWorker(__name__, app, log_worker, features.LOG_EXPORT)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.LOG_EXPORT:
        logger.debug("Log export not enabled; skipping")
        while True:
            time.sleep(100000)

    logger.debug("Starting export action logs worker")
    worker = ExportActionLogsWorker(
        export_action_logs_queue, poll_period_seconds=POLL_PERIOD_SECONDS
    )
    worker.start()
