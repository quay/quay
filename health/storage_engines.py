import logging

logger = logging.getLogger(__name__)


def check_storage_engines(stor, http_client):
    """Validate all configured storage engines and return (ok, message).

    Iterates every location in ``stor.locations`` and calls ``stor.validate``
    on each one individually.  A failure on a preferred location (or on any
    location when no preferred locations are configured) causes the overall
    check to return ``(False, msg)``.  Failures on non-preferred locations are
    downgraded to warnings and included in the message without changing the
    boolean result.
    """
    preferred = set(stor.preferred_locations)
    failures = []
    warnings = []

    for location in stor.locations:
        try:
            stor.validate([location], http_client)
        except Exception as ex:
            # Fail closed: if no preferred locations are set, every location is
            # treated as preferred so a total outage is never silently ignored.
            if not preferred or location in preferred:
                logger.exception("Preferred storage '%s' check failed: %s", location, ex)
                failures.append("Preferred storage '%s' check failed: %s" % (location, ex))
            else:
                logger.warning("Non-preferred storage '%s' unavailable: %s", location, ex)
                warnings.append("Non-preferred storage '%s' unavailable: %s" % (location, ex))

    if failures:
        msg = "; ".join(failures)
        if warnings:
            msg += " (warnings: %s)" % "; ".join(warnings)
        return (False, msg)

    return (True, "; ".join(warnings) if warnings else None)
