import logging

from gzip import GzipFile
from tempfile import SpooledTemporaryFile

from app import build_logs, log_archive, app
from data.archivedlogs import JSON_MIMETYPE
from data.database import CloseForLongOperation
from util.streamingjsonencoder import StreamingJSONEncoder
from workers.buildlogsarchiver.models_pre_oci import pre_oci_model as model
from workers.worker import Worker


logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 30
MEMORY_TEMPFILE_SIZE = 64 * 1024  # Large enough to handle approximately 99% of builds in memory


class ArchiveBuildLogsWorker(Worker):
    def __init__(self):
        super(ArchiveBuildLogsWorker, self).__init__()
        self.add_operation(self._archive_redis_buildlogs, POLL_PERIOD_SECONDS)

    def _archive_redis_buildlogs(self):
        """
        Archive a single build, choosing a candidate at random.

        This process must be idempotent to avoid needing two-phase commit.
        """
        # Get a random build to archive
        to_archive = model.get_archivable_build()
        if to_archive is None:
            logger.debug("No more builds to archive")
            return

        logger.debug("Archiving: %s", to_archive.uuid)

        length, entries = build_logs.get_log_entries(to_archive.uuid, 0)
        to_encode = {
            "start": 0,
            "total": length,
            "logs": entries,
        }

        if length > 0:
            with CloseForLongOperation(app.config):
                with SpooledTemporaryFile(MEMORY_TEMPFILE_SIZE) as tempfile:
                    with GzipFile("testarchive", fileobj=tempfile) as zipstream:
                        for chunk in StreamingJSONEncoder().iterencode(to_encode):
                            zipstream.write(chunk.encode("utf-8"))

                    tempfile.seek(0)
                    log_archive.store_file(
                        tempfile, JSON_MIMETYPE, content_encoding="gzip", file_id=to_archive.uuid
                    )

        we_updated = model.mark_build_archived(to_archive.uuid)
        if we_updated:
            build_logs.expire_status(to_archive.uuid)
            build_logs.delete_log_entries(to_archive.uuid)
        else:
            logger.debug("Another worker pre-empted us when archiving: %s", to_archive.uuid)


if __name__ == "__main__":
    worker = ArchiveBuildLogsWorker()
    worker.start()
