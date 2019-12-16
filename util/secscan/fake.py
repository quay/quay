import json
import copy
import uuid
import urllib.parse

from contextlib import contextmanager
from httmock import urlmatch, HTTMock, all_requests

from util.secscan.api import UNKNOWN_PARENT_LAYER_ERROR_MSG, compute_layer_id


@contextmanager
def fake_security_scanner(hostname="fakesecurityscanner"):
    """
    Context manager which yields a fake security scanner.

    All requests made to the given hostname (default: fakesecurityscanner) will be handled by the
    fake.
    """
    scanner = FakeSecurityScanner(hostname)
    with HTTMock(*(scanner.get_endpoints())):
        yield scanner


class FakeSecurityScanner(object):
    """
    Implements a fake security scanner (with somewhat real responses) for testing API calls and
    responses.
    """

    def __init__(self, hostname, index_version=1):
        self.hostname = hostname
        self.index_version = index_version
        self.layers = {}
        self.notifications = {}
        self.layer_vulns = {}

        self.ok_layer_id = None
        self.fail_layer_id = None
        self.internal_error_layer_id = None
        self.error_layer_id = None
        self.unexpected_status_layer_id = None

    def set_ok_layer_id(self, ok_layer_id):
        """
        Sets a layer ID that, if encountered when the analyze call is made, causes a 200 to be
        immediately returned.
        """
        self.ok_layer_id = ok_layer_id

    def set_fail_layer_id(self, fail_layer_id):
        """
        Sets a layer ID that, if encountered when the analyze call is made, causes a 422 to be
        raised.
        """
        self.fail_layer_id = fail_layer_id

    def set_internal_error_layer_id(self, internal_error_layer_id):
        """
        Sets a layer ID that, if encountered when the analyze call is made, causes a 500 to be
        raised.
        """
        self.internal_error_layer_id = internal_error_layer_id

    def set_error_layer_id(self, error_layer_id):
        """
        Sets a layer ID that, if encountered when the analyze call is made, causes a 400 to be
        raised.
        """
        self.error_layer_id = error_layer_id

    def set_unexpected_status_layer_id(self, layer_id):
        """
        Sets a layer ID that, if encountered when the analyze call is made, causes an HTTP 600 to be
        raised.

        This is useful in testing the robustness of the to unknown status codes.
        """
        self.unexpected_status_layer_id = layer_id

    def has_layer(self, layer_id):
        """
        Returns true if the layer with the given ID has been analyzed.
        """
        return layer_id in self.layers

    def has_notification(self, notification_id):
        """
        Returns whether a notification with the given ID is found in the scanner.
        """
        return notification_id in self.notifications

    def add_notification(
        self,
        old_layer_ids,
        new_layer_ids,
        old_vuln,
        new_vuln,
        max_per_page=100,
        indexed_old_layer_ids=None,
        indexed_new_layer_ids=None,
    ):
        """
        Adds a new notification over the given sets of layer IDs and vulnerability information,
        returning the structural data of the notification created.
        """
        notification_id = str(uuid.uuid4())
        if old_vuln is None:
            old_vuln = dict(new_vuln)

        self.notifications[notification_id] = dict(
            old_layer_ids=old_layer_ids,
            new_layer_ids=new_layer_ids,
            old_vuln=old_vuln,
            new_vuln=new_vuln,
            max_per_page=max_per_page,
            indexed_old_layer_ids=indexed_old_layer_ids,
            indexed_new_layer_ids=indexed_new_layer_ids,
        )

        return self._get_notification_data(notification_id, 0, 100)

    def layer_id(self, layer):
        """
        Returns the Quay Security Scanner layer ID for the given layer (Image row).
        """
        return compute_layer_id(layer)

    def add_layer(self, layer_id):
        """
        Adds a layer to the security scanner, with no features or vulnerabilities.
        """
        self.layers[layer_id] = {
            "Name": layer_id,
            "Format": "Docker",
            "IndexedByVersion": self.index_version,
        }

    def remove_layer(self, layer_id):
        """
        Removes a layer from the security scanner.
        """
        self.layers.pop(layer_id, None)

    def set_vulns(self, layer_id, vulns):
        """
        Sets the vulnerabilities for the layer with the given ID to those given.
        """
        self.layer_vulns[layer_id] = vulns

        # Since this call may occur before the layer is "anaylzed", we only add the data
        # to the layer itself if present.
        if self.layers.get(layer_id):
            layer = self.layers[layer_id]
            layer["Features"] = layer.get("Features", [])
            layer["Features"].append(
                {
                    "Name": "somefeature",
                    "Namespace": "somenamespace",
                    "Version": "someversion",
                    "Vulnerabilities": self.layer_vulns[layer_id],
                }
            )

    def _get_notification_data(self, notification_id, page, limit):
        """
        Returns the structural data for the notification with the given ID, paginated using the
        given page and limit.
        """
        notification = self.notifications[notification_id]
        limit = min(limit, notification["max_per_page"])

        notification_data = {
            "Name": notification_id,
            "Created": "1456247389",
            "Notified": "1456246708",
            "Limit": limit,
        }

        start_index = page * limit
        end_index = (page + 1) * limit
        has_additional_page = False

        if notification.get("old_vuln"):
            old_layer_ids = notification["old_layer_ids"]
            old_layer_ids = old_layer_ids[start_index:end_index]
            has_additional_page = has_additional_page or bool(len(old_layer_ids[end_index - 1 :]))

            notification_data["Old"] = {
                "Vulnerability": notification["old_vuln"],
                "LayersIntroducingVulnerability": old_layer_ids,
            }

            if notification.get("indexed_old_layer_ids", None):
                indexed_old_layer_ids = notification["indexed_old_layer_ids"][start_index:end_index]
                notification_data["Old"][
                    "OrderedLayersIntroducingVulnerability"
                ] = indexed_old_layer_ids

        if notification.get("new_vuln"):
            new_layer_ids = notification["new_layer_ids"]
            new_layer_ids = new_layer_ids[start_index:end_index]
            has_additional_page = has_additional_page or bool(len(new_layer_ids[end_index - 1 :]))

            notification_data["New"] = {
                "Vulnerability": notification["new_vuln"],
                "LayersIntroducingVulnerability": new_layer_ids,
            }

            if notification.get("indexed_new_layer_ids", None):
                indexed_new_layer_ids = notification["indexed_new_layer_ids"][start_index:end_index]
                notification_data["New"][
                    "OrderedLayersIntroducingVulnerability"
                ] = indexed_new_layer_ids

        if has_additional_page:
            notification_data["NextPage"] = str(page + 1)

        return notification_data

    def get_endpoints(self):
        """
        Returns the HTTMock endpoint definitions for the fake security scanner.
        """

        @urlmatch(netloc=r"(.*\.)?" + self.hostname, path=r"/v1/layers/(.+)", method="GET")
        def get_layer_mock(url, request):
            layer_id = url.path[len("/v1/layers/") :]
            if layer_id == self.ok_layer_id:
                return {
                    "status_code": 200,
                    "content": json.dumps({"Layer": {}}),
                }

            if layer_id == self.internal_error_layer_id:
                return {
                    "status_code": 500,
                    "content": json.dumps({"Error": {"Message": "Internal server error"}}),
                }

            if not layer_id in self.layers:
                return {
                    "status_code": 404,
                    "content": json.dumps({"Error": {"Message": "Unknown layer"}}),
                }

            layer_data = copy.deepcopy(self.layers[layer_id])

            has_vulns = request.url.find("vulnerabilities") > 0
            has_features = request.url.find("features") > 0
            if not has_vulns and not has_features:
                layer_data.pop("Features", None)

            return {
                "status_code": 200,
                "content": json.dumps({"Layer": layer_data}),
            }

        @urlmatch(netloc=r"(.*\.)?" + self.hostname, path=r"/v1/layers/(.+)", method="DELETE")
        def remove_layer_mock(url, _):
            layer_id = url.path[len("/v1/layers/") :]
            if not layer_id in self.layers:
                return {
                    "status_code": 404,
                    "content": json.dumps({"Error": {"Message": "Unknown layer"}}),
                }

            self.layers.pop(layer_id)
            return {
                "status_code": 204,
                "content": "",
            }

        @urlmatch(netloc=r"(.*\.)?" + self.hostname, path=r"/v1/layers", method="POST")
        def post_layer_mock(_, request):
            body_data = json.loads(request.body)
            if not "Layer" in body_data:
                return {"status_code": 400, "content": "Missing body"}

            layer = body_data["Layer"]
            if not "Path" in layer:
                return {"status_code": 400, "content": "Missing Path"}

            if not "Name" in layer:
                return {"status_code": 400, "content": "Missing Name"}

            if not "Format" in layer:
                return {"status_code": 400, "content": "Missing Format"}

            if layer["Name"] == self.internal_error_layer_id:
                return {
                    "status_code": 500,
                    "content": json.dumps({"Error": {"Message": "Internal server error"}}),
                }

            if layer["Name"] == self.fail_layer_id:
                return {
                    "status_code": 422,
                    "content": json.dumps({"Error": {"Message": "Cannot analyze"}}),
                }

            if layer["Name"] == self.error_layer_id:
                return {
                    "status_code": 400,
                    "content": json.dumps({"Error": {"Message": "Some sort of error"}}),
                }

            if layer["Name"] == self.unexpected_status_layer_id:
                return {
                    "status_code": 600,
                    "content": json.dumps({"Error": {"Message": "Some sort of error"}}),
                }

            parent_id = layer.get("ParentName", None)
            parent_layer = None

            if parent_id is not None:
                parent_layer = self.layers.get(parent_id, None)
                if parent_layer is None:
                    return {
                        "status_code": 400,
                        "content": json.dumps(
                            {"Error": {"Message": UNKNOWN_PARENT_LAYER_ERROR_MSG}}
                        ),
                    }

            self.add_layer(layer["Name"])
            if parent_layer is not None:
                self.layers[layer["Name"]]["ParentName"] = parent_id

            # If vulnerabilities have already been registered with this layer, call set_vulns to make sure
            # their data is added to the layer's data.
            if self.layer_vulns.get(layer["Name"]):
                self.set_vulns(layer["Name"], self.layer_vulns[layer["Name"]])

            return {
                "status_code": 201,
                "content": json.dumps({"Layer": self.layers[layer["Name"]],}),
            }

        @urlmatch(
            netloc=r"(.*\.)?" + self.hostname, path=r"/v1/notifications/(.+)$", method="DELETE"
        )
        def delete_notification(url, _):
            notification_id = url.path[len("/v1/notifications/") :]
            if notification_id not in self.notifications:
                return {
                    "status_code": 404,
                    "content": json.dumps({"Error": {"Message": "Unknown notification"}}),
                }

            self.notifications.pop(notification_id)
            return {
                "status_code": 204,
                "content": "",
            }

        @urlmatch(netloc=r"(.*\.)?" + self.hostname, path=r"/v1/notifications/(.+)$", method="GET")
        def get_notification(url, _):
            notification_id = url.path[len("/v1/notifications/") :]
            if notification_id not in self.notifications:
                return {
                    "status_code": 404,
                    "content": json.dumps({"Error": {"Message": "Unknown notification"}}),
                }

            query_params = urllib.parse.parse_qs(url.query)
            limit = int(query_params.get("limit", [2])[0])
            page = int(query_params.get("page", [0])[0])

            notification_data = self._get_notification_data(notification_id, page, limit)
            response = {"Notification": notification_data}
            return {
                "status_code": 200,
                "content": json.dumps(response),
            }

        @urlmatch(netloc=r"(.*\.)?" + self.hostname, path=r"/v1/metrics$", method="GET")
        def metrics(url, _):
            return {
                "status_code": 200,
                "content": json.dumps({"fake": True}),
            }

        @all_requests
        def response_content(url, _):
            return {
                "status_code": 500,
                "content": json.dumps({"Error": {"Message": "Unknown endpoint %s" % url.path}}),
            }

        return [
            get_layer_mock,
            post_layer_mock,
            remove_layer_mock,
            get_notification,
            delete_notification,
            metrics,
            response_content,
        ]
