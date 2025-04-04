import pytest

from data.database import DeletedNamespace, User
from endpoints.api.superuser import (
    SuperUserDumpConfig,
    SuperUserList,
    SuperUserManagement,
    SuperUserOrganizationList,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "disabled",
    [
        (True),
        (False),
    ],
)
def test_list_all_users(disabled, app):
    with client_with_identity("devtable", app) as cl:
        params = {"disabled": disabled}
        result = conduct_api_call(cl, SuperUserList, "GET", params, None, 200).json
        assert len(result["users"])
        for user in result["users"]:
            if not disabled:
                assert user["enabled"]


def test_list_all_orgs(app):
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, SuperUserOrganizationList, "GET", None, None, 200).json
        assert len(result["organizations"]) == 8


def test_paginate_orgs(app):
    with client_with_identity("devtable", app) as cl:
        params = {"limit": 4}
        firstResult = conduct_api_call(cl, SuperUserOrganizationList, "GET", params, None, 200).json
        assert len(firstResult["organizations"]) == 4
        assert firstResult["next_page"] is not None
        params["next_page"] = firstResult["next_page"]
        secondResult = conduct_api_call(
            cl, SuperUserOrganizationList, "GET", params, None, 200
        ).json
        assert len(secondResult["organizations"]) == 4
        assert secondResult.get("next_page", None) is None


def test_paginate_test_list_all_users(app):
    with client_with_identity("devtable", app) as cl:
        params = {"limit": 7}
        firstResult = conduct_api_call(cl, SuperUserList, "GET", params, None, 200).json
        assert len(firstResult["users"]) == 7
        assert firstResult["next_page"] is not None
        params["next_page"] = firstResult["next_page"]
        secondResult = conduct_api_call(cl, SuperUserList, "GET", params, None, 200).json
        assert len(secondResult["users"]) == 6
        assert secondResult.get("next_page", None) is None


def test_change_install_user(app):
    with client_with_identity("devtable", app) as cl:
        params = {"username": "randomuser"}
        body = {"email": "new_email123@test.com"}
        result = conduct_api_call(cl, SuperUserManagement, "PUT", params, body, 200).json

        assert result["email"] == body["email"]


def test_get_superuserdumpconfig(app):
    import features

    features.import_features({"FEATURE_SUPERUSER_CONFIGDUMP": True})
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, SuperUserDumpConfig, "GET", None, None, 200).json
        # we check for json struct to be returned by the function
        assert isinstance(result.get("config", False), dict)
        assert isinstance(result.get("warning", False), dict)
        assert isinstance(result.get("env", False), dict)
        assert isinstance(result.get("schema", False), dict)

        # we check for some Keys that are expected to be always present
        with pytest.raises(AttributeError):
            result.get("config", {})["AUTHENTICATION_TYPE"]
            result.get("config", {})["SERVER_HOSTNAME"]
            # satisfy the test after passing without KeyError raised
            raise AttributeError()
        # we check for some Keys that are expected to be present in warning
        # which means, they are not in config.yaml but set by the application
        with pytest.raises(AttributeError):
            result.get("warning", {})["APPLICATION_ROOT"]
            result.get("warning", {})["EXPLAIN_TEMPLATE_LOADING"]
            # satisfy the test after passing without KeyError raised
            raise AttributeError()
        # we check for some Keys that are expected to be present in env
        with pytest.raises(AttributeError):
            result.get("env", {})["PATH"]
            result.get("env", {})["PYTHONPATH"]
            # satisfy the test after passing without KeyError raised
            raise AttributeError()
        # we check for some Keys that are expected to be present in schema
        with pytest.raises(AttributeError):
            result.get("schema", {})["description"]
            result.get("schema", {})["required"]
            raise AttributeError()
