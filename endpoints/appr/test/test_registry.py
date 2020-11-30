import base64
import json

from mock import patch

import pytest

from flask import url_for

from data import model
from endpoints.appr.registry import appr_bp

from test.fixtures import *


@pytest.mark.parametrize(
    "login_data, expected_code",
    [
        ({"username": "devtable", "password": "password"}, 200),
        ({"username": "devtable", "password": "badpass"}, 401),
        ({"username": "devtable+dtrobot", "password": "badpass"}, 401),
        ({"username": "devtable+dtrobot2", "password": "badpass"}, 401),
    ],
)
def test_login(login_data, expected_code, app, client):
    if "+" in login_data["username"] and login_data["password"] is None:
        username, robotname = login_data["username"].split("+")
        _, login_data["password"] = model.user.create_robot(
            robotname, model.user.get_user(username)
        )

    url = url_for("appr.login")
    headers = {"Content-Type": "application/json"}
    data = {"user": login_data}

    rv = client.open(url, method="POST", data=json.dumps(data), headers=headers)
    assert rv.status_code == expected_code


@pytest.mark.parametrize(
    "release_name",
    [
        "1.0",
        "1",
        1,
    ],
)
def test_invalid_release_name(release_name, app, client):
    params = {
        "namespace": "devtable",
        "package_name": "someapprepo",
    }

    url = url_for("appr.push", **params)
    auth = base64.b64encode(b"devtable:password").decode("ascii")
    headers = {"Content-Type": "application/json", "Authorization": "Basic " + auth}
    data = {
        "release": release_name,
        "media_type": "application/vnd.cnr.manifest.v1+json",
        "blob": "H4sIAFQwWVoAA+3PMQrCQBAF0Bxlb+Bk143nETGIIEoSC29vMMFOu3TvNb/5DH/Ot8f02jWbiohDremT3ZKR90uuUlty7nKJNmqKtkQuTarbzlo8x+k4zFOu4+lyH4afvbnW93/urH98EwAAAAAAAAAAADb0BsdwExIAKAAA",
    }

    rv = client.open(url, method="POST", data=json.dumps(data), headers=headers)
    assert rv.status_code == 422


@pytest.mark.parametrize(
    "readonly, expected_status",
    [
        (True, 405),
        (False, 422),
    ],
)
def test_readonly(readonly, expected_status, app, client):
    params = {
        "namespace": "devtable",
        "package_name": "someapprepo",
    }

    url = url_for("appr.push", **params)
    auth = base64.b64encode(b"devtable:password").decode("ascii")
    headers = {"Content-Type": "application/json", "Authorization": "Basic " + auth}
    data = {
        "release": "1.0",
        "media_type": "application/vnd.cnr.manifest.v0+json",
        "blob": "H4sIAFQwWVoAA+3PMQrCQBAF0Bxlb+Bk143nETGIIEoSC29vMMFOu3TvNb/5DH/Ot8f02jWbiohDremT3ZKR90uuUlty7nKJNmqKtkQuTarbzlo8x+k4zFOu4+lyH4afvbnW93/urH98EwAAAAAAAAAAADb0BsdwExIAKAAA",
    }

    with patch("endpoints.appr.models_cnr.model.is_readonly", readonly):
        rv = client.open(url, method="POST", data=json.dumps(data), headers=headers)
        assert rv.status_code == expected_status
