import logging

from datetime import datetime
from util.timedeltastring import convert_to_timedelta

logger = logging.getLogger(__name__)


def _expires_after(label_dict, tag, model):
    """
    Sets the expiration of a manifest based on the quay.expires-in label.
    """
    try:
        timedelta = convert_to_timedelta(label_dict["value"])
    except ValueError:
        logger.exception("Could not convert %s to timedeltastring", label_dict["value"])
        return False

    if timedelta.total_seconds() <= 0:
        return False

    logger.debug("Labeling tag %s with expiration of %s", tag, timedelta)
    model.change_repository_tag_expiration(tag, datetime.utcnow() + timedelta)
    return True


_LABEL_HANDLERS = {
    "quay.expires-after": _expires_after,
}


def tag_label_action_keys():
    """ Returns the set of label keys to lookup for applying labels to a tag. """
    return _LABEL_HANDLERS.keys()


def apply_label_to_tag(label_dict, tag, model):
    """
    Runs the handler defined, if any, for the given label. Returns True if a change was made.
    """
    handler = _LABEL_HANDLERS.get(label_dict["key"])
    if handler is not None:
        return handler(label_dict, tag, model)

    return False
