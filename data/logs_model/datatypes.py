import json

from calendar import timegm
from collections import namedtuple
from email.utils import formatdate

from cachetools.func import lru_cache

from data import model
from util.morecollections import AttrDict


def _format_date(date):
    """
    Output an RFC822 date format.
    """
    if date is None:
        return None

    return formatdate(timegm(date.utctimetuple()))


@lru_cache(maxsize=1)
def _kinds():
    return model.log.get_log_entry_kinds()


class LogEntriesPage(namedtuple("LogEntriesPage", ["logs", "next_page_token"])):
    """
    Represents a page returned by the lookup_logs call.

    The `logs` contains the logs found for the page and `next_page_token`, if not None, contains the
    token to be encoded and returned for the followup call.
    """


class Log(
    namedtuple(
        "Log",
        [
            "metadata_json",
            "ip",
            "datetime",
            "performer_email",
            "performer_username",
            "performer_robot",
            "account_organization",
            "account_username",
            "account_email",
            "account_robot",
            "kind_id",
        ],
    )
):
    """
    Represents a single log entry returned by the logs model.
    """

    @classmethod
    def for_logentry(cls, log):
        account_organization = None
        account_username = None
        account_email = None
        account_robot = None

        try:
            account_organization = log.account.organization
            account_username = log.account.username
            account_email = log.account.email
            account_robot = log.account.robot
        except AttributeError:
            pass

        performer_robot = None
        performer_username = None
        performer_email = None

        try:
            performer_robot = log.performer.robot
            performer_username = log.performer.username
            performer_email = log.performer.email
        except AttributeError:
            pass

        return Log(
            log.metadata_json,
            log.ip,
            log.datetime,
            performer_email,
            performer_username,
            performer_robot,
            account_organization,
            account_username,
            account_email,
            account_robot,
            log.kind_id,
        )

    @classmethod
    def for_elasticsearch_log(cls, log, id_user_map):
        account_organization = None
        account_username = None
        account_email = None
        account_robot = None

        try:
            if log.account_id:
                account = id_user_map[log.account_id]
                account_organization = account.organization
                account_username = account.username
                account_email = account.email
                account_robot = account.robot
        except AttributeError:
            pass

        performer_robot = None
        performer_username = None
        performer_email = None

        try:
            if log.performer_id:
                performer = id_user_map[log.performer_id]
                performer_robot = performer.robot
                performer_username = performer.username
                performer_email = performer.email
        except AttributeError:
            pass

        return Log(
            json.dumps(log.metadata.to_dict()),
            str(log.ip),
            log.datetime,
            performer_email,
            performer_username,
            performer_robot,
            account_organization,
            account_username,
            account_email,
            account_robot,
            log.kind_id,
        )

    def to_dict(self, avatar, include_namespace=False):
        view = {
            "kind": _kinds()[self.kind_id],
            "metadata": json.loads(self.metadata_json or "{}"),
            "ip": self.ip,
            "datetime": _format_date(self.datetime),
        }

        if self.performer_username:
            performer = AttrDict(
                {"username": self.performer_username, "email": self.performer_email}
            )
            performer.robot = None
            if self.performer_robot:
                performer.robot = self.performer_robot

            view["performer"] = {
                "kind": "user",
                "name": self.performer_username,
                "is_robot": self.performer_robot,
                "avatar": avatar.get_data_for_user(performer),
            }

        if include_namespace:
            if self.account_username:
                account = AttrDict({"username": self.account_username, "email": self.account_email})
                if self.account_organization:

                    view["namespace"] = {
                        "kind": "org",
                        "name": self.account_username,
                        "avatar": avatar.get_data_for_org(account),
                    }
                else:
                    account.robot = None
                    if self.account_robot:
                        account.robot = self.account_robot
                    view["namespace"] = {
                        "kind": "user",
                        "name": self.account_username,
                        "avatar": avatar.get_data_for_user(account),
                    }

        return view


class AggregatedLogCount(namedtuple("AggregatedLogCount", ["kind_id", "count", "datetime"])):
    """
    Represents the aggregated count of the number of logs, of a particular kind, on a day.
    """

    def to_dict(self):
        view = {
            "kind": _kinds()[self.kind_id],
            "count": self.count,
            "datetime": _format_date(self.datetime),
        }

        return view
