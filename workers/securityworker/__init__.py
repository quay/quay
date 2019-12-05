import logging.config

from prometheus_client import Gauge

from app import app, prometheus
from data.database import UseThenDisconnect
from workers.securityworker.models_pre_oci import pre_oci_model as model
from util.secscan.api import APIRequestFailure
from util.secscan.analyzer import PreemptedException


logger = logging.getLogger(__name__)


unscanned_images = Gauge(
    "quay_security_scanning_unscanned_images_remaining",
    "number of images that are not scanned by the latest security scanner",
)


def index_images(target_version, analyzer, token=None):
    """ Performs security indexing of all images in the database not scanned at the target version.
      If a token is provided, scanning will begin where the token indicates it previously completed. """
    iterator, next_token = model.candidates_to_scan(target_version, start_token=token)
    if iterator is None:
        logger.debug("Found no additional images to scan")
        return None

    with UseThenDisconnect(app.config):
        for candidate, abt, num_remaining in iterator:
            try:
                analyzer.analyze_recursively(candidate)
            except PreemptedException:
                logger.info("Another worker pre-empted us for layer: %s", candidate.id)
                abt.set()
            except APIRequestFailure:
                logger.exception("Security scanner service unavailable")
                return

            unscanned_images.set(num_remaining)

    return next_token
