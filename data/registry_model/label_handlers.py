import logging

from util.timedeltastring import convert_to_timedelta

logger = logging.getLogger(__name__)


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


_LABEL_HANDLERS = {
    "quay.expires-after": _expires_after,
}


def apply_label_to_manifest(label_dict, manifest, model):
    """
    Runs the handler defined, if any, for the given label.
    """
    handler = _LABEL_HANDLERS.get(label_dict["key"])
    if handler is not None:
        handler(label_dict, manifest, model)
