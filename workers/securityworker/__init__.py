import logging.config

from app import app, prometheus
from data.database import UseThenDisconnect
from workers.securityworker.models_pre_oci import pre_oci_model as model
from util.secscan.api import APIRequestFailure
from util.secscan.analyzer import PreemptedException

logger = logging.getLogger(__name__)
unscanned_images_gauge = prometheus.create_gauge(
    "unscanned_images", "Number of images that clair needs to scan."
)


def index_images(target_version, analyzer, token=None):
    """ Performs security indexing of all images in the database not scanned at the target version.
      If a token is provided, scanning will begin where the token indicates it previously completed.
  """
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

            unscanned_images_gauge.Set(num_remaining)

    return next_token
