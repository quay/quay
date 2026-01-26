import logging

import features
from util.timedeltastring import convert_to_timedelta

logger = logging.getLogger(__name__)


LABEL_EXPIRY_KEY = "quay.expires-after"
LABEL_IMMUTABLE_KEY = "quay.immutable"


def _expires_after(label_dict, manifest, model):
    """
    Sets the expiration of a manifest based on the quay.expires-in label.
    """
    try:
        timedelta = convert_to_timedelta(label_dict["value"])
    except ValueError:
        logger.exception("Could not convert %s to timedeltastring", label_dict["value"])
        return

    total_seconds = timedelta.total_seconds()
    logger.debug("Labeling manifest %s with expiration of %s", manifest, total_seconds)
    model.set_tags_expiration_for_manifest(manifest, total_seconds)


def _immutable(label_dict, manifest, model):
    """
    Sets immutability on manifest tags based on the quay.immutable label.
    """
    if not features.IMMUTABLE_TAGS:
        return

    value = label_dict.get("value", "").strip().lower()
    if value == "true":
        logger.debug("Labeling manifest %s as immutable", manifest)
        model.set_tags_immutability_for_manifest(manifest, True)


_LABEL_HANDLERS = {
    LABEL_EXPIRY_KEY: _expires_after,
    LABEL_IMMUTABLE_KEY: _immutable,
}


def apply_label_to_manifest(label_dict, manifest, model):
    """
    Runs the handler defined, if any, for the given label.
    """
    handler = _LABEL_HANDLERS.get(label_dict["key"])
    if handler is not None:
        handler(label_dict, manifest, model)
