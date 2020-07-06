import uuid
import json

from calendar import timegm

from data import model


class SharedModel:
    def queue_logs_export(
        self,
        start_datetime,
        end_datetime,
        export_action_logs_queue,
        namespace_name=None,
        repository_name=None,
        callback_url=None,
        callback_email=None,
        filter_kinds=None,
    ):
        """
        Queues logs between the start_datetime and end_time, filtered by a repository or namespace,
        for export to the specified URL and/or email address.

        Returns the ID of the export job queued or None if error.
        """
        export_id = str(uuid.uuid4())
        namespace = model.user.get_namespace_user(namespace_name)
        if namespace is None:
            return None

        repository = None
        if repository_name is not None:
            repository = model.repository.get_repository(namespace_name, repository_name)
            if repository is None:
                return None

        export_action_logs_queue.put(
            [namespace_name],
            json.dumps(
                {
                    "export_id": export_id,
                    "repository_id": repository.id if repository else None,
                    "namespace_id": namespace.id,
                    "namespace_name": namespace.username,
                    "repository_name": repository.name if repository else None,
                    "start_time": start_datetime.strftime("%m/%d/%Y"),
                    "end_time": end_datetime.strftime("%m/%d/%Y"),
                    "callback_url": callback_url,
                    "callback_email": callback_email,
                }
            ),
            retries_remaining=3,
        )

        return export_id


def epoch_ms(dt):
    return (timegm(dt.timetuple()) * 1000) + (dt.microsecond // 1000)


def get_kinds_filter(kinds):
    """
    Given a list of kinds, return the set of kinds not that are not part of that list.

    i.e Returns the list of kinds to be filtered out.
    """
    kind_map = model.log.get_log_entry_kinds()
    kind_map = {key: kind_map[key] for key in kind_map if not isinstance(key, int)}
    return [kind_name for kind_name in kind_map if kind_name not in kinds]
