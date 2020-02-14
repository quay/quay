import json
from datetime import datetime


class LogEntryJSONEncoder(json.JSONEncoder):
    """
    JSON encoder to encode datetimes to ISO8601 format.
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        return super(LogEntryJSONEncoder, self).default(obj)


def logs_json_serializer(logentry, sort_keys=False):
    """
    Serializes a LogEntry to json bytes.
    """
    return json.dumps(
        logentry.to_dict(), cls=LogEntryJSONEncoder, ensure_ascii=True, sort_keys=sort_keys
    ).encode("ascii")
