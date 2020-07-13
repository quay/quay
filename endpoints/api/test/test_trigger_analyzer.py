import pytest
from mock import Mock

from auth import permissions
from data import model
from endpoints.api.trigger_analyzer import TriggerAnalyzer
from util import dockerfileparse
from test.fixtures import *
from app import app as real_app

BAD_PATH = '"server_hostname/" is not a valid Quay repository path'

EMPTY_CONF = {}

GOOD_CONF = {"context": "/", "dockerfile_path": "/file"}

BAD_CONF = {"context": "context", "dockerfile_path": "dockerfile_path"}

ONE_ROBOT = {"can_read": False, "is_robot": True, "kind": "user", "name": "namespace+name"}

DOCKERFILE_NOT_CHILD = "Dockerfile, context, is not a child of the context, dockerfile_path."

THE_DOCKERFILE_SPECIFIED = "Could not parse the Dockerfile specified"

DOCKERFILE_PATH_NOT_FOUND = "Specified Dockerfile path for the trigger was not found on the main branch. This trigger may fail."

NO_FROM_LINE = "No FROM line found in the Dockerfile"

REPO_NOT_FOUND = 'Repository "server_hostname/path/file" referenced by the Dockerfile was not found'


@pytest.fixture
def get_monkeypatch(monkeypatch):
    return monkeypatch


def patch_permissions(monkeypatch, can_read=False):
    def can_read_fn(base_namespace, base_repository):
        return can_read

    monkeypatch.setattr(permissions, "ReadRepositoryPermission", can_read_fn)


def patch_list_namespace_robots(monkeypatch):
    my_mock = Mock()
    my_mock.configure_mock(**{"username": "namespace+name"})
    return_value = [my_mock]

    def return_list_mocks(namesapce):
        return return_value

    monkeypatch.setattr(model.user, "list_namespace_robots", return_list_mocks)
    return return_value


def patch_get_all_repo_users_transitive(monkeypatch):
    my_mock = Mock()
    my_mock.configure_mock(**{"username": "name"})
    return_value = [my_mock]

    def return_get_mocks(namesapce, image_repostiory):
        return return_value

    monkeypatch.setattr(model.user, "get_all_repo_users_transitive", return_get_mocks)
    return return_value


def patch_parse_dockerfile(monkeypatch, get_base_image):
    if get_base_image is not None:

        def return_return_value(content):
            parse_mock = Mock()
            parse_mock.configure_mock(**{"get_base_image": get_base_image})
            return parse_mock

        monkeypatch.setattr(dockerfileparse, "parse_dockerfile", return_return_value)
    else:

        def return_return_value(content):
            return get_base_image

        monkeypatch.setattr(dockerfileparse, "parse_dockerfile", return_return_value)


def patch_model_repository_get_repository(monkeypatch, get_repository):
    if get_repository is not None:

        def mock_get_repository(base_namespace, base_repository):
            vis_mock = Mock()
            vis_mock.name = get_repository
            get_repo_mock = Mock(visibility=vis_mock)

            return get_repo_mock

    else:

        def mock_get_repository(base_namespace, base_repository):
            return None

    monkeypatch.setattr(model.repository, "get_repository", mock_get_repository)


def return_none():
    return None


def return_content():
    return Mock()


def return_server_hostname():
    return "server_hostname/"


def return_non_server_hostname():
    return "slime"


def return_path():
    return "server_hostname/path/file"


@pytest.mark.parametrize(
    "handler_fn, config_dict, admin_org_permission, status, message, get_base_image, robots, server_hostname, get_repository, can_read, namespace, name",
    [
        pytest.param(
            return_none,
            EMPTY_CONF,
            False,
            "warning",
            DOCKERFILE_PATH_NOT_FOUND,
            None,
            [],
            None,
            None,
            False,
            "namespace",
            None,
            id="test1",
        ),
        pytest.param(
            return_none,
            EMPTY_CONF,
            True,
            "warning",
            DOCKERFILE_PATH_NOT_FOUND,
            None,
            [ONE_ROBOT],
            None,
            None,
            False,
            "namespace",
            None,
            id="test2",
        ),
        pytest.param(
            return_content,
            BAD_CONF,
            False,
            "error",
            THE_DOCKERFILE_SPECIFIED,
            None,
            [],
            None,
            None,
            False,
            "namespace",
            None,
            id="test3",
        ),
        pytest.param(
            return_none,
            EMPTY_CONF,
            False,
            "warning",
            DOCKERFILE_PATH_NOT_FOUND,
            return_none,
            [],
            None,
            None,
            False,
            "namespace",
            None,
            id="test4",
        ),
        pytest.param(
            return_none,
            EMPTY_CONF,
            True,
            "warning",
            DOCKERFILE_PATH_NOT_FOUND,
            return_none,
            [ONE_ROBOT],
            None,
            None,
            False,
            "namespace",
            None,
            id="test5",
        ),
        pytest.param(
            return_content,
            BAD_CONF,
            False,
            "error",
            DOCKERFILE_NOT_CHILD,
            return_none,
            [],
            None,
            None,
            False,
            "namespace",
            None,
            id="test6",
        ),
        pytest.param(
            return_content,
            GOOD_CONF,
            False,
            "warning",
            NO_FROM_LINE,
            return_none,
            [],
            None,
            None,
            False,
            "namespace",
            None,
            id="test7",
        ),
        pytest.param(
            return_content,
            GOOD_CONF,
            False,
            "publicbase",
            None,
            return_non_server_hostname,
            [],
            "server_hostname",
            None,
            False,
            "namespace",
            None,
            id="test8",
        ),
        pytest.param(
            return_content,
            GOOD_CONF,
            False,
            "warning",
            BAD_PATH,
            return_server_hostname,
            [],
            "server_hostname",
            None,
            False,
            "namespace",
            None,
            id="test9",
        ),
        pytest.param(
            return_content,
            GOOD_CONF,
            False,
            "error",
            REPO_NOT_FOUND,
            return_path,
            [],
            "server_hostname",
            None,
            False,
            "namespace",
            None,
            id="test10",
        ),
        pytest.param(
            return_content,
            GOOD_CONF,
            False,
            "error",
            REPO_NOT_FOUND,
            return_path,
            [],
            "server_hostname",
            "nonpublic",
            False,
            "namespace",
            None,
            id="test11",
        ),
        pytest.param(
            return_content,
            GOOD_CONF,
            False,
            "publicbase",
            None,
            return_path,
            [],
            "server_hostname",
            "public",
            True,
            "path",
            "file",
            id="test12",
        ),
    ],
)
def test_trigger_analyzer(
    handler_fn,
    config_dict,
    admin_org_permission,
    status,
    message,
    get_base_image,
    robots,
    server_hostname,
    get_repository,
    can_read,
    namespace,
    name,
    get_monkeypatch,
    client,
):
    patch_list_namespace_robots(get_monkeypatch)
    patch_get_all_repo_users_transitive(get_monkeypatch)
    patch_parse_dockerfile(get_monkeypatch, get_base_image)
    patch_model_repository_get_repository(get_monkeypatch, get_repository)
    patch_permissions(get_monkeypatch, can_read)
    handler_mock = Mock()
    handler_mock.configure_mock(**{"load_dockerfile_contents": handler_fn})
    trigger_analyzer = TriggerAnalyzer(
        handler_mock, "namespace", server_hostname, config_dict, admin_org_permission
    )
    assert trigger_analyzer.analyze_trigger() == {
        "namespace": namespace,
        "name": name,
        "robots": robots,
        "status": status,
        "message": message,
        "is_admin": admin_org_permission,
    }


class FakeHandler(object):
    def load_dockerfile_contents(self):
        return """
            FROM localhost:5000/devtable/simple
        """


def test_inherited_robot_accounts(get_monkeypatch, initialized_db, client):
    patch_permissions(get_monkeypatch, False)
    analyzer = TriggerAnalyzer(FakeHandler(), "anothernamespace", "localhost:5000", {}, True)
    assert analyzer.analyze_trigger()["status"] == "error"


def test_inherited_robot_accounts_same_namespace(get_monkeypatch, initialized_db, client):
    patch_permissions(get_monkeypatch, True)
    analyzer = TriggerAnalyzer(FakeHandler(), "devtable", "localhost:5000", {}, True)

    result = analyzer.analyze_trigger()
    assert result["status"] == "requiresrobot"
    for robot in result["robots"]:
        assert robot["name"].startswith("devtable+")
        assert "token" not in robot


def test_inherited_robot_accounts_same_namespace_no_read_permission(
    get_monkeypatch, initialized_db, client
):
    patch_permissions(get_monkeypatch, False)
    analyzer = TriggerAnalyzer(FakeHandler(), "devtable", "localhost:5000", {}, True)

    result = analyzer.analyze_trigger()
    assert analyzer.analyze_trigger()["status"] == "error"


def test_inherited_robot_accounts_same_namespace_not_org_admin(
    get_monkeypatch, initialized_db, client
):
    patch_permissions(get_monkeypatch, True)
    analyzer = TriggerAnalyzer(FakeHandler(), "devtable", "localhost:5000", {}, False)

    result = analyzer.analyze_trigger()
    assert result["status"] == "requiresrobot"
    assert not result["robots"]
