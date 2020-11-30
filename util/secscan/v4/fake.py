import json

from collections import defaultdict
from contextlib import contextmanager
from httmock import urlmatch, HTTMock, all_requests


@contextmanager
def fake_security_scanner(hostname="fakesecurityscanner", incompatible=False):
    """
    Context manager which yields a fake security scanner.

    All requests made to the given hostname (default: fakesecurityscanner) will be handled by the
    fake. If `incompatible is True`, returns malformed responses to test if a client can handle
    version skew.
    """
    scanner = FakeSecurityScanner(hostname)
    if not incompatible:
        with HTTMock(*scanner.endpoints):
            yield scanner
    else:
        with HTTMock(*scanner.incompatible_endpoints):
            yield scanner


class FakeSecurityScanner(object):
    """
    Implements a fake security scanner (with somewhat real responses) for testing API calls and
    responses.
    """

    def __init__(self, hostname):
        self.hostname = hostname
        self.indexer_state = "abc"

        self.manifests = {}
        self.index_reports = {}
        self.vulnerability_reports = {}
        self.notifications = defaultdict(list)

    def add_notification(self, notification_id, manifest_digest, reason, vulnerability):
        """
        Adds a notification to be returned by the fake.
        """
        self.notifications[notification_id].append(
            {
                "id": notification_id,
                "manifest": manifest_digest,
                "reason": reason,
                "vulnerability": vulnerability,
            }
        )

    @property
    def endpoints(self):
        """
        The HTTMock endpoint definitions for the fake security scanner.
        """

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname, path=r"/indexer/api/v1/index_state", method="GET"
        )
        def state(url, request):
            return {"status_code": 200, "content": json.dumps({"state": self.indexer_state})}

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname, path=r"/indexer/api/v1/index_report", method="POST"
        )
        def index(url, request):
            body = json.loads(request.body)
            if not "hash" in body or not "layers" in body:
                return {
                    "status_code": 400,
                    "content": json.dumps(
                        {"code": "bad-request", "message": "failed to deserialize manifest"}
                    ),
                }

            report = {
                "manifest_hash": body["hash"],
                "state": "IndexFinished",
                "packages": {},
                "distributions": {},
                "repository": {},
                "environments": {},
                "success": True,
                "err": "",
            }
            self.index_reports[body["hash"]] = report
            self.vulnerability_reports[body["hash"]] = {
                "manifest_hash": body["hash"],
                "packages": {},
                "distributions": {},
                "environments": {},
                "vulnerabilities": {},
                "package_vulnerabilities": {},
            }
            self.manifests[body["hash"]] = body

            return {
                "status_code": 201,
                "content": json.dumps(report),
                "headers": {
                    "etag": self.indexer_state,
                },
            }

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname,
            path=r"/indexer/api/v1/index_report/(.+)",
            method="GET",
        )
        def index_report(url, request):
            manifest_hash = url.path[len("/indexer/api/v1/index_report/") :]
            if manifest_hash not in self.index_reports:
                return {
                    "status_code": 404,
                    "content": json.dumps(
                        {
                            "code": "not-found",
                            "message": 'index report for manifest "'
                            + manifest_hash
                            + '" not found',
                        }
                    ),
                }

            return {
                "status_code": 200,
                "content": json.dumps(self.index_reports[manifest_hash]),
                "headers": {
                    "etag": self.indexer_state,
                },
            }

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname,
            path=r"/matcher/api/v1/vulnerability_report/(.+)",
            method="GET",
        )
        def vulnerability_report(url, request):
            manifest_hash = url.path[len("/matcher/api/v1/vulnerability_report/") :]
            if manifest_hash not in self.index_reports:
                return {
                    "status_code": 404,
                    "content": json.dumps(
                        {
                            "code": "not-found",
                            "message": 'index report for manifest "'
                            + manifest_hash
                            + '" not found',
                        }
                    ),
                }

            return {
                "status_code": 200,
                "content": json.dumps(self.vulnerability_reports[manifest_hash]),
                "headers": {
                    "etag": self.indexer_state,
                },
            }

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname,
            path=r"/notifier/api/v1/notification/(.+)",
            method="GET",
        )
        def get_notification(url, request):
            notification_id = url.path[len("/notifier/api/v1/notification/") :]
            if notification_id not in self.notifications:
                return {
                    "status_code": 404,
                    "content": json.dumps(
                        {"code": "not-found", "message": "notification not found"}
                    ),
                }

            return {
                "status_code": 200,
                "content": json.dumps(
                    {
                        "notifications": self.notifications[notification_id],
                        "page": {
                            "size": len(self.notifications[notification_id]),
                        },
                    }
                ),
                "headers": {
                    "etag": self.indexer_state,
                },
            }

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname,
            path=r"/notifier/api/v1/notification/(.+)",
            method="DELETE",
        )
        def delete_notification(url, request):
            notification_id = url.path[len("/notifier/api/v1/notification/") :]
            if notification_id not in self.notifications:
                return {
                    "status_code": 404,
                    "content": json.dumps(
                        {"code": "not-found", "message": "notification not found"}
                    ),
                }

            del self.notifications[notification_id]

            return {
                "status_code": 204,
                "content": json.dumps({}),
                "headers": {
                    "etag": self.indexer_state,
                },
            }

        @all_requests
        def response_content(url, _):
            return {
                "status_code": 404,
                "content": "404 page not found",
            }

        return [
            state,
            index,
            index_report,
            vulnerability_report,
            get_notification,
            delete_notification,
            response_content,
        ]

    @property
    def incompatible_endpoints(self):
        """
        The HTTMock endpoint definitions for the fake security scanner which returns incompatible responses.
        """

        @all_requests
        def response_content(url, _):
            return {
                "status_code": 200,
                "content": json.dumps({"foo": "bar"}),
            }

        return [response_content]
