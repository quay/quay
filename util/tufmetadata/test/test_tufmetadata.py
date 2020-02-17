import pytest
import requests
from mock import mock, patch

from flask import Flask

from test import testconfig
from test.fixtures import init_db_path
from util.tufmetadata import api


valid_response = {
    "signed": {
        "type": "Targets",
        "delegations": {"keys": {}, "roles": {},},
        "expires": "2020-03-30T18:55:26.594764859-04:00",
        "targets": {
            "latest": {
                "hashes": {"sha256": "mLmxwTyUrqIRDaz8uaBapfrp3GPERfsDg2kiMujlteo="},
                "length": 1500,
            }
        },
        "version": 2,
    },
    "signatures": [
        {
            "method": "ecdsa",
            "sig": "yYnJGsYAYEL9PSwXisdG7JUEM1YK2IIKM147K3fWJthF4w+vl3xOm67r5ZNuDK6ss/Ff+x8yljZdT3sE/Hg5mw==",
        }
    ],
}

valid_targets_with_delegation = {
    "signed": {
        "_type": "Targets",
        "delegations": {
            "keys": {
                "5e71c65cb1ba794f253fa377c970a237799745adab92024522b12f5b2f1d3031": {
                    "keytype": "ecdsa-x509",
                    "keyval": {
                        "private": None,
                        "public": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUI4akNDQVppZ0F3SUJBZ0lVTDIxVm5aakZFZ0hFTjV5OFhHbUJZWi9ta1U4d0NnWUlLb1pJemowRUF3SXcKU0RFTE1Ba0dBMVVFQmhNQ1ZWTXhDekFKQmdOVkJBZ1RBa05CTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJRd0VnWURWUVFERXd0bGVHRnRjR3hsTG01bGREQWVGdzB4TnpBMU1Ea3dNVEkyTURCYUZ3MHhPREExCk1Ea3dNVEkyTURCYU1DUXhJakFnQmdOVkJBTVRHWE4wWVdkcGJtY3VjWFZoZVM1cGJ5OXhkV0Y1TDNGMVlYa3cKV1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVNmbVFSQmpJeUw2WHdoSW0zbnE4TEtLSXJqT3czVApmU2ZMUmMyQlhQeU9uS2EvandvaVdBdHlMSFdwcmlJNTlBM2ZtbmtHK1FUVlBlMkJGTUNrS0xMQ280R0RNSUdBCk1BNEdBMVVkRHdFQi93UUVBd0lGb0RBVEJnTlZIU1VFRERBS0JnZ3JCZ0VGQlFjREFUQU1CZ05WSFJNQkFmOEUKQWpBQU1CMEdBMVVkRGdRV0JCUk96NjFUS2wxd1B5aTJPdWJ3dmlURkZYVlB4REFmQmdOVkhTTUVHREFXZ0JSVgpBbGl0dVZWajF3RXIwaVZhMjcwN244S3htakFMQmdOVkhSRUVCREFDZ2dBd0NnWUlLb1pJemowRUF3SURTQUF3ClJRSWdHaVZGTUprNDNWYVBRNHJ0S1BhNGp3amIxcjF0b05vTE5KTzhlRU02OSs0Q0lRRHl1VXk5cFFwTXFmU3gKelRiNVB5SjJ0STI5bHdkem0yVUZsSDhRd0FPTnhRPT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
                    },
                },
                "78cf3c9de9d59f61391bfa183cfdc676ab4e9b179cf5c1c42019a5271d2542b0": {
                    "keytype": "ecdsa-x509",
                    "keyval": {
                        "private": None,
                        "public": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUIrVENDQWFDZ0F3SUJBZ0lVZkxPV0FzT2x5UjZaSVYxS1UrTW56K2pYekY4d0NnWUlLb1pJemowRUF3SXcKU0RFTE1Ba0dBMVVFQmhNQ1ZWTXhDekFKQmdOVkJBZ1RBa05CTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJRd0VnWURWUVFERXd0bGVHRnRjR3hsTG01bGREQWVGdzB4TnpBMU1UQXhPRFUxTURCYUZ3MHhPREExCk1UQXhPRFUxTURCYU1Dd3hLakFvQmdOVkJBTVRJWE4wWVdkcGJtY3VjWFZoZVM1cGJ5OXhkV0Y1TDNGMVlYa3QKYzNSaFoybHVaekJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUFCT2hnMCtxdTRtTHFPaEVQOC8zZAp0YXBMaHlwbHBoNGlaQkZMekpQNjlqTEJJSnN4aTdGTkxvZzBJY2tYQnNndmNRMFFEdE9XT3k0TFhBQ3Nqc0FzCndmQ2pnWU13Z1lBd0RnWURWUjBQQVFIL0JBUURBZ1dnTUJNR0ExVWRKUVFNTUFvR0NDc0dBUVVGQndNQk1Bd0cKQTFVZEV3RUIvd1FDTUFBd0hRWURWUjBPQkJZRUZMNCtDVXBLYm5YeHU1OXRQbzE2aFNWK21hTE1NQjhHQTFVZApJd1FZTUJhQUZFbzA5QU9keGNwSnAxaVJZSyt0V1JOMlltSGZNQXNHQTFVZEVRUUVNQUtDQURBS0JnZ3Foa2pPClBRUURBZ05IQURCRUFpQTVLN20vb0g0clZTTTloUmFGc3lWUzhWVTlQNzhCVHJaZ2xERjFKSFFkblFJZ0thcTMKbzRLcjBoelRzMng3cFVtWFZlWW4xbGJaRlRaZXJ3QzhTcXhtVHBZPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
                    },
                },
                "ada8b980813a887f007a1c42376c35a81cbba3b1090aae16cbffedb9004934c8": {
                    "keytype": "ecdsa-x509",
                    "keyval": {
                        "private": None,
                        "public": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUIrakNDQWFDZ0F3SUJBZ0lVTUdzU0hyMWZLK3htaG81STFJdStIcXEzbjZ3d0NnWUlLb1pJemowRUF3SXcKU0RFTE1Ba0dBMVVFQmhNQ1ZWTXhDekFKQmdOVkJBZ1RBa05CTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJRd0VnWURWUVFERXd0bGVHRnRjR3hsTG01bGREQWVGdzB4TnpBMU1UQXdNVEl4TURCYUZ3MHhPREExCk1UQXdNVEl4TURCYU1Dd3hLakFvQmdOVkJBTVRJWE4wWVdkcGJtY3VjWFZoZVM1cGJ5OXhkV0Y1TDNGMVlYa3QKYzNSaFoybHVaekJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUFCRlY4YVBhTjMzTE5HSWtMTVFnZwpJYjk1VzF5aGEvblpLYm1vdXF4c0VOdWhYZitUZmZnUjlIOVFsMHVIaVJQTzZWRFhKMU90K2h6eDk5SGVMdHRQClRCeWpnWU13Z1lBd0RnWURWUjBQQVFIL0JBUURBZ1dnTUJNR0ExVWRKUVFNTUFvR0NDc0dBUVVGQndNQk1Bd0cKQTFVZEV3RUIvd1FDTUFBd0hRWURWUjBPQkJZRUZFZHVRVThaei83THUrdGxod0lyYWM0ZmFGNmVNQjhHQTFVZApJd1FZTUJhQUZEK21iblFMUXlHTmcxMFc2dUxHcDRGSldRNnBNQXNHQTFVZEVRUUVNQUtDQURBS0JnZ3Foa2pPClBRUURBZ05JQURCRkFpQlB6Z2x3OFYyaHhKWXM2WDFrNE9hb255bkx2b3hxbGJweFJtWkRaNmFwcGdJaEFJd1oKdmp1MFpQYjZuaGZWTkF5b3dNM09XdEFVYm95eEZCcDBxd2FYMzFYSgotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
                    },
                },
                "e2727632903bf9d0ac6856c6e4f8cb44f443c220ecf51e2fb6b465c7d85b9169": {
                    "keytype": "ecdsa-x509",
                    "keyval": {
                        "private": None,
                        "public": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUI4ekNDQVppZ0F3SUJBZ0lVWS9IdzVKL2lkTzA3M3BMR2U0b3BxZytpcVBrd0NnWUlLb1pJemowRUF3SXcKU0RFTE1Ba0dBMVVFQmhNQ1ZWTXhDekFKQmdOVkJBZ1RBa05CTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJRd0VnWURWUVFERXd0bGVHRnRjR3hsTG01bGREQWVGdzB4TnpBMU1Ea3hOekl6TURCYUZ3MHhPREExCk1Ea3hOekl6TURCYU1DUXhJakFnQmdOVkJBTVRHWE4wWVdkcGJtY3VjWFZoZVM1cGJ5OXhkV0Y1TDNGMVlYa3cKV1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVRrMFl0VmdWRHZpbnpwM1g3NHhOS0tKK2hldVptWgpqeWgwZnQ2Ny8yQ1NnU1MwLzVtRUNtR2dJbDc5WXlsV3VRdHZkYnFrSWVNWkU1M0RkQnlnZUcrcm80R0RNSUdBCk1BNEdBMVVkRHdFQi93UUVBd0lGb0RBVEJnTlZIU1VFRERBS0JnZ3JCZ0VGQlFjREFUQU1CZ05WSFJNQkFmOEUKQWpBQU1CMEdBMVVkRGdRV0JCUzM5TnNydHZndmhlL0hhQk1CSzdvQjZ4R3ZGVEFmQmdOVkhTTUVHREFXZ0JTdwoybDdYYkJsbXVYeTZvcGdNMGF0c3ViMWJOVEFMQmdOVkhSRUVCREFDZ2dBd0NnWUlLb1pJemowRUF3SURTUUF3ClJnSWhBSjNRdThUNWdPdzVKaVNyT3c2TEtBNnZnRGduKzNEMEJJYzB2UENzd05XbkFpRUE4VW93dVBoaFE0MEMKTFY3dkhDN0t1QTBULzZLY2dLT1Rpb1VNR2FFM2MzRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
                    },
                },
            },
            "roles": [
                {
                    "keyids": [
                        "e2727632903bf9d0ac6856c6e4f8cb44f443c220ecf51e2fb6b465c7d85b9169",
                        "ada8b980813a887f007a1c42376c35a81cbba3b1090aae16cbffedb9004934c8",
                        "78cf3c9de9d59f61391bfa183cfdc676ab4e9b179cf5c1c42019a5271d2542b0",
                        "5e71c65cb1ba794f253fa377c970a237799745adab92024522b12f5b2f1d3031",
                    ],
                    "name": "targets/devs",
                    "paths": [""],
                    "threshold": 1,
                }
            ],
        },
        "expires": "2020-05-09T15:06:27.189711073-04:00",
        "targets": {},
        "version": 4,
    },
    "signatures": [
        {
            "keyid": "3353687138116a5950603adbcb449e4e84e61523fb4a43c7dde33d1d2e40a934",
            "method": "ecdsa",
            "sig": "dbuUBGQ5FdcuRxzg9SCMQ7mym5w4xxdTezWqq9UTj4GHU75pEaTHo1oZEEud+ofI66gjA6hmqljdnOsEQ6CTYw==",
        }
    ],
}


valid_delegation = {
    "signed": {
        "_type": "Targets",
        "delegations": {"keys": {}, "roles": []},
        "expires": "2020-05-09T15:25:05.840775035-04:00",
        "targets": {
            "191e5d9": {
                "hashes": {"sha256": "DE7i9XN+sd8vkdsJWSLlujKsATmTffzzhGBPsVYRFmg="},
                "length": 46683,
            },
            "977ae7a": {
                "hashes": {"sha256": "a3e7naDPcCfMEJAv0JgmJ0h+qZQoGNDrdgwpN/5B5YY="},
                "length": 46682,
            },
            "b96b871": {
                "hashes": {"sha256": "j662F+e+3eN5QBSaFLFj24khbfWIffz24f5HGLrkyvw="},
                "length": 46680,
            },
        },
        "version": 5,
    },
    "signatures": [
        {
            "keyid": "78cf3c9de9d59f61391bfa183cfdc676ab4e9b179cf5c1c42019a5271d2542b0",
            "method": "ecdsa",
            "sig": "ZLW5DokQw3ipFGsS3I9d6xkUdFlKS1vuvtlR3/I9lGdQZUa+QfpdpiEhKIO92aTCsDZvBn1m4wwb0MukLH8fgA==",
        }
    ],
}


@pytest.mark.parametrize(
    "tuf_prefix,server_hostname,namespace,repo,gun",
    [
        ("quay.dev", "quay.io", "ns", "repo", "quay.dev/ns/repo"),
        (None, "quay.io", "ns", "repo", "quay.io/ns/repo"),
        ("quay.dev/", "quay.io", "ns", "repo", "quay.dev/ns/repo"),
        (None, "quay.io/", "ns", "repo", "quay.io/ns/repo"),
        (None, "localhost:5000/", "ns", "repo", "localhost:5000/ns/repo"),
        (None, "localhost:5000", "ns", "repo", "localhost:5000/ns/repo"),
    ],
)
def test_gun(tuf_prefix, server_hostname, namespace, repo, gun):
    app = Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    app.config["TUF_GUN_PREFIX"] = tuf_prefix
    app.config["SERVER_HOSTNAME"] = server_hostname
    tuf_api = api.TUFMetadataAPI(app, app.config)
    assert gun == tuf_api._gun(namespace, repo)


@pytest.mark.parametrize(
    "response_code,response_body,expected",
    [
        (
            200,
            valid_response,
            (valid_response["signed"]["targets"], "2020-03-30T18:55:26.594764859-04:00"),
        ),
        (200, {"garbage": "data"}, (None, None)),
    ],
)
def test_get_default_tags(response_code, response_body, expected):
    app = Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    client = mock.Mock()
    request = mock.Mock(status_code=response_code)
    request.json.return_value = response_body
    client.request.return_value = request
    tuf_api = api.TUFMetadataAPI(app, app.config, client=client)
    response = tuf_api.get_default_tags_with_expiration("quay", "quay")
    assert response == expected


@pytest.mark.parametrize(
    "response_code,response_body1,response_body2,expected",
    [
        (
            200,
            valid_targets_with_delegation,
            valid_delegation,
            {
                "targets/devs": {
                    "targets": valid_delegation["signed"]["targets"],
                    "expiration": valid_delegation["signed"]["expires"],
                }
            },
        ),
        (200, {"garbage": "data"}, {"garbage": "data"}, {"targets": None}),
    ],
)
def test_get_all_tags(response_code, response_body1, response_body2, expected):
    app = Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    client = mock.Mock()
    request = mock.Mock(status_code=response_code)
    request.json.side_effect = [response_body1, response_body2, {}, {}, {}, {}]
    client.request.return_value = request
    tuf_api = api.TUFMetadataAPI(app, app.config, client=client)
    response = tuf_api.get_all_tags_with_expiration("quay", "quay")
    assert response == expected


@pytest.mark.parametrize(
    "connection_error,response_code,exception",
    [
        (True, 200, requests.exceptions.Timeout),
        (True, 200, requests.exceptions.ConnectionError),
        (False, 200, requests.exceptions.RequestException),
        (False, 200, ValueError),
        (True, 500, api.Non200ResponseException(mock.Mock(status_code=500))),
        (False, 400, api.Non200ResponseException(mock.Mock(status_code=400))),
        (False, 404, api.Non200ResponseException(mock.Mock(status_code=404))),
        (False, 200, api.InvalidMetadataException),
    ],
)
def test_get_metadata_exception(connection_error, response_code, exception):
    app = Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    request = mock.Mock(status_code=response_code)
    client = mock.Mock(request=request)
    client.request.side_effect = exception
    tuf_api = api.TUFMetadataAPI(app, app.config, client=client)
    tags, expiration = tuf_api.get_default_tags_with_expiration("quay", "quay")
    assert tags == None
    assert expiration == None


@pytest.mark.parametrize("response_code,expected", [(200, True), (400, False), (401, False),])
def test_delete_metadata(response_code, expected):
    app = Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    client = mock.Mock()
    request = mock.Mock(status_code=response_code)
    client.request.return_value = request
    tuf_api = api.TUFMetadataAPI(app, app.config, client=client)
    response = tuf_api.delete_metadata("quay", "quay")
    assert response == expected


@pytest.mark.parametrize(
    "response_code,exception",
    [
        (200, requests.exceptions.Timeout),
        (200, requests.exceptions.ConnectionError),
        (200, requests.exceptions.RequestException),
        (200, ValueError),
        (500, api.Non200ResponseException(mock.Mock(status_code=500))),
        (400, api.Non200ResponseException(mock.Mock(status_code=400))),
        (401, api.Non200ResponseException(mock.Mock(status_code=401))),
        (404, api.Non200ResponseException(mock.Mock(status_code=404))),
    ],
)
def test_delete_metadata_exception(response_code, exception):
    app = Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    request = mock.Mock(status_code=response_code)
    client = mock.Mock(request=request)
    client.request.side_effect = exception
    tuf_api = api.TUFMetadataAPI(app, app.config, client=client)
    response = tuf_api.delete_metadata("quay", "quay")
    assert response == False
