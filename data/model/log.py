import json
import logging

from datetime import datetime, timedelta
from calendar import timegm
from cachetools.func import lru_cache

from peewee import JOIN, fn, PeeweeException

from data.database import LogEntryKind, User, RepositoryActionCount, db, LogEntry3
from data.model import config, user, DataModelException

logger = logging.getLogger(__name__)

ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING = ["pull_repo"]


def _logs_query(
    selections,
    start_time=None,
    end_time=None,
    performer=None,
    repository=None,
    namespace=None,
    ignore=None,
    model=LogEntry3,
    id_range=None,
    namespace_id=None,
):
    """
    Returns a query for selecting logs from the table, with various options and filters.
    """
    if namespace is not None:
        assert namespace_id is None

    if namespace_id is not None:
        assert namespace is None

    assert (start_time is not None and end_time is not None) or (id_range is not None)
    joined = model.select(*selections).switch(model)

    if id_range is not None:
        joined = joined.where(model.id >= id_range[0], model.id <= id_range[1])
    else:
        joined = joined.where(model.datetime >= start_time, model.datetime < end_time)

    if repository:
        joined = joined.where(model.repository == repository)

    if performer:
        joined = joined.where(model.performer == performer)

    if namespace and not repository:
        namespace_user = user.get_user_or_org(namespace)
        if namespace_user is None:
            raise DataModelException("Invalid namespace requested: %s" % namespace)

        joined = joined.where(model.account == namespace_user.id)

    if namespace_id is not None and not repository:
        joined = joined.where(model.account == namespace_id)

    if ignore:
        kind_map = get_log_entry_kinds()
        ignore_ids = [kind_map[kind_name] for kind_name in ignore]
        joined = joined.where(~(model.kind << ignore_ids))

    return joined


def _latest_logs_query(
    selections,
    performer=None,
    repository=None,
    namespace=None,
    ignore=None,
    model=LogEntry3,
    size=None,
):
    """
    Returns a query for selecting the latest logs from the table, with various options and filters.
    """
    query = model.select(*selections).switch(model)

    if repository:
        query = query.where(model.repository == repository)

    if performer:
        query = query.where(model.repository == repository)

    if namespace and not repository:
        namespace_user = user.get_user_or_org(namespace)
        if namespace_user is None:
            raise DataModelException("Invalid namespace requested")

        query = query.where(model.account == namespace_user.id)

    if ignore:
        kind_map = get_log_entry_kinds()
        ignore_ids = [kind_map[kind_name] for kind_name in ignore]
        query = query.where(~(model.kind << ignore_ids))

    query = query.order_by(model.datetime.desc(), model.id)

    if size:
        query = query.limit(size)

    return query


@lru_cache(maxsize=1)
def get_log_entry_kinds():
    kind_map = {}
    for kind in LogEntryKind.select():
        kind_map[kind.id] = kind.name
        kind_map[kind.name] = kind.id

    return kind_map


def _get_log_entry_kind(name):
    kinds = get_log_entry_kinds()
    return kinds[name]


def get_aggregated_logs(
    start_time,
    end_time,
    performer=None,
    repository=None,
    namespace=None,
    ignore=None,
    model=LogEntry3,
):
    """
    Returns the count of logs, by kind and day, for the logs matching the given filters.
    """
    date = db.extract_date("day", model.datetime)
    selections = [model.kind, date.alias("day"), fn.Count(model.id).alias("count")]
    query = _logs_query(
        selections, start_time, end_time, performer, repository, namespace, ignore, model=model
    )
    return query.group_by(date, model.kind)


def get_logs_query(
    start_time=None,
    end_time=None,
    performer=None,
    repository=None,
    namespace=None,
    namespace_id=None,
    ignore=None,
    model=LogEntry3,
    id_range=None,
):
    """
    Returns the logs matching the given filters.
    """
    Performer = User.alias()
    Account = User.alias()
    selections = [model, Performer]

    if namespace is None and repository is None and namespace_id is None:
        selections.append(Account)

    query = _logs_query(
        selections,
        start_time,
        end_time,
        performer,
        repository,
        namespace,
        ignore,
        model=model,
        id_range=id_range,
        namespace_id=namespace_id,
    )
    query = query.switch(model).join(
        Performer, JOIN.LEFT_OUTER, on=(model.performer == Performer.id).alias("performer")
    )

    if namespace is None and repository is None and namespace_id is None:
        query = query.switch(model).join(
            Account, JOIN.LEFT_OUTER, on=(model.account == Account.id).alias("account")
        )

    return query


def get_latest_logs_query(
    performer=None, repository=None, namespace=None, ignore=None, model=LogEntry3, size=None
):
    """
    Returns the latest logs matching the given filters.
    """
    Performer = User.alias()
    Account = User.alias()
    selections = [model, Performer]

    if namespace is None and repository is None:
        selections.append(Account)

    query = _latest_logs_query(
        selections, performer, repository, namespace, ignore, model=model, size=size
    )
    query = query.switch(model).join(
        Performer, JOIN.LEFT_OUTER, on=(model.performer == Performer.id).alias("performer")
    )

    if namespace is None and repository is None:
        query = query.switch(model).join(
            Account, JOIN.LEFT_OUTER, on=(model.account == Account.id).alias("account")
        )

    return query


def _json_serialize(obj):
    if isinstance(obj, datetime):
        return timegm(obj.utctimetuple())

    return obj


def log_action(
    kind_name,
    user_or_organization_name,
    performer=None,
    repository=None,
    ip=None,
    metadata={},
    timestamp=None,
):
    """
    Logs an entry in the LogEntry table.
    """
    if not timestamp:
        timestamp = datetime.today()

    account = None
    if user_or_organization_name is not None:
        account = User.get(User.username == user_or_organization_name).id
    else:
        account = config.app_config.get("SERVICE_LOG_ACCOUNT_ID")
        if account is None:
            account = user.get_minimum_user_id()

    if performer is not None:
        performer = performer.id

    if repository is not None:
        repository = repository.id

    kind = _get_log_entry_kind(kind_name)
    metadata_json = json.dumps(metadata, default=_json_serialize)
    log_data = {
        "kind": kind,
        "account": account,
        "performer": performer,
        "repository": repository,
        "ip": ip,
        "metadata_json": metadata_json,
        "datetime": timestamp,
    }

    try:
        LogEntry3.create(**log_data)
    except PeeweeException as ex:
        strict_logging_disabled = config.app_config.get("ALLOW_PULLS_WITHOUT_STRICT_LOGGING")
        if strict_logging_disabled and kind_name in ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING:
            logger.exception("log_action failed", extra=({"exception": ex}).update(log_data))
        else:
            raise


def get_stale_logs_start_id(model):
    """
    Gets the oldest log entry.
    """
    try:
        return (model.select(fn.Min(model.id)).tuples())[0][0]
    except IndexError:
        return None


def get_stale_logs(start_id, end_id, model, cutoff_date):
    """
    Returns all the logs with IDs between start_id and end_id inclusively.
    """
    return model.select().where(
        (model.id >= start_id), (model.id <= end_id), model.datetime <= cutoff_date
    )


def delete_stale_logs(start_id, end_id, model):
    """
    Deletes all the logs with IDs between start_id and end_id.
    """
    model.delete().where((model.id >= start_id), (model.id <= end_id)).execute()


def get_repository_action_counts(repo, start_date):
    """
    Returns the daily aggregated action counts for the given repository, starting at the given start
    date.
    """
    return RepositoryActionCount.select().where(
        RepositoryActionCount.repository == repo, RepositoryActionCount.date >= start_date
    )


def get_repositories_action_sums(repository_ids):
    """
    Returns a map from repository ID to total actions within that repository in the last week.
    """
    if not repository_ids:
        return {}

    # Filter the join to recent entries only.
    last_week = datetime.now() - timedelta(weeks=1)
    tuples = (
        RepositoryActionCount.select(
            RepositoryActionCount.repository, fn.Sum(RepositoryActionCount.count)
        )
        .where(RepositoryActionCount.repository << repository_ids)
        .where(RepositoryActionCount.date >= last_week)
        .group_by(RepositoryActionCount.repository)
        .tuples()
    )

    action_count_map = {}
    for record in tuples:
        action_count_map[record[0]] = record[1]

    return action_count_map


def get_minimum_id_for_logs(start_time, repository_id=None, namespace_id=None, model=LogEntry3):
    """
    Returns the minimum ID for logs matching the given repository or namespace in the logs table,
    starting at the given start time.
    """
    # First try bounded by a day. Most repositories will meet this criteria, and therefore
    # can make a much faster query.
    day_after = start_time + timedelta(days=1)
    result = _get_bounded_id(
        fn.Min,
        model.datetime >= start_time,
        repository_id,
        namespace_id,
        model.datetime < day_after,
        model=model,
    )
    if result is not None:
        return result

    return _get_bounded_id(
        fn.Min, model.datetime >= start_time, repository_id, namespace_id, model=model
    )


def get_maximum_id_for_logs(end_time, repository_id=None, namespace_id=None, model=LogEntry3):
    """
    Returns the maximum ID for logs matching the given repository or namespace in the logs table,
    ending at the given end time.
    """
    # First try bounded by a day. Most repositories will meet this criteria, and therefore
    # can make a much faster query.
    day_before = end_time - timedelta(days=1)
    result = _get_bounded_id(
        fn.Max,
        model.datetime <= end_time,
        repository_id,
        namespace_id,
        model.datetime > day_before,
        model=model,
    )
    if result is not None:
        return result

    return _get_bounded_id(
        fn.Max, model.datetime <= end_time, repository_id, namespace_id, model=model
    )


def _get_bounded_id(
    fn, filter_clause, repository_id, namespace_id, reduction_clause=None, model=LogEntry3
):
    assert (namespace_id is not None) or (repository_id is not None)
    query = model.select(fn(model.id)).where(filter_clause)

    if reduction_clause is not None:
        query = query.where(reduction_clause)

    if repository_id is not None:
        query = query.where(model.repository == repository_id)
    else:
        query = query.where(model.account == namespace_id)

    row = query.tuples()[0]
    if not row:
        return None

    return row[0]
