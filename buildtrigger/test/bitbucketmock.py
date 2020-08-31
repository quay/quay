from datetime import datetime
from mock import Mock

from buildtrigger.bitbuckethandler import BitbucketBuildTrigger
from util.morecollections import AttrDict


def get_bitbucket_trigger(dockerfile_path=""):
    trigger_obj = AttrDict(dict(auth_token="foobar", id="sometrigger"))
    trigger = BitbucketBuildTrigger(
        trigger_obj,
        {
            "build_source": "foo/bar",
            "dockerfile_path": dockerfile_path,
            "nickname": "knownuser",
            "account_id": "foo",
        },
    )

    trigger._get_client = get_mock_bitbucket
    return trigger


def get_repo_path_contents(path, revision):
    data = {
        "files": [{"path": "Dockerfile"}],
    }

    return (True, data, None)


def get_raw_path_contents(path, revision):
    if path == "Dockerfile":
        return (True, "hello world", None)

    if path == "somesubdir/Dockerfile":
        return (True, "hi universe", None)

    return (False, None, None)


def get_branches_and_tags():
    data = {
        "branches": [{"name": "master"}, {"name": "otherbranch"}],
        "tags": [{"name": "sometag"}, {"name": "someothertag"}],
    }
    return (True, data, None)


def get_branches():
    return (True, {"master": {}, "otherbranch": {}}, None)


def get_tags():
    return (True, {"sometag": {}, "someothertag": {}}, None)


def get_branch(branch_name):
    if branch_name != "master":
        return (False, None, None)

    data = {
        "target": {
            "hash": "aaaaaaa",
        },
    }

    return (True, data, None)


def get_tag(tag_name):
    if tag_name != "sometag":
        return (False, None, None)

    data = {
        "target": {
            "hash": "aaaaaaa",
        },
    }

    return (True, data, None)


def get_changeset_mock(commit_sha):
    if commit_sha != "aaaaaaa":
        return (False, None, "Not found")

    data = {
        "node": "aaaaaaa",
        "message": "some message",
        "timestamp": "now",
        "raw_author": "foo@bar.com",
    }

    return (True, data, None)


def get_changesets():
    changesets_mock = Mock()
    changesets_mock.get = Mock(side_effect=get_changeset_mock)
    return changesets_mock


def get_deploykeys():
    deploykeys_mock = Mock()
    deploykeys_mock.create = Mock(return_value=(True, {"pk": "someprivatekey"}, None))
    deploykeys_mock.delete = Mock(return_value=(True, {}, None))
    return deploykeys_mock


def get_webhooks():
    webhooks_mock = Mock()
    webhooks_mock.create = Mock(return_value=(True, {"uuid": "someuuid"}, None))
    webhooks_mock.delete = Mock(return_value=(True, {}, None))
    return webhooks_mock


def get_repo_mock(name):
    if name != "bar":
        return None

    repo_mock = Mock()
    repo_mock.get_main_branch = Mock(return_value=(True, {"name": "master"}, None))
    repo_mock.get_path_contents = Mock(side_effect=get_repo_path_contents)
    repo_mock.get_raw_path_contents = Mock(side_effect=get_raw_path_contents)
    repo_mock.get_branches_and_tags = Mock(side_effect=get_branches_and_tags)
    repo_mock.get_branches = Mock(side_effect=get_branches)
    repo_mock.get_tags = Mock(side_effect=get_tags)
    repo_mock.get_branch = Mock(side_effect=get_branch)
    repo_mock.get_tag = Mock(side_effect=get_tag)

    repo_mock.changesets = Mock(side_effect=get_changesets)
    repo_mock.deploykeys = Mock(side_effect=get_deploykeys)
    repo_mock.webhooks = Mock(side_effect=get_webhooks)
    return repo_mock


def get_repositories_mock():
    repos_mock = Mock()
    repos_mock.get = Mock(side_effect=get_repo_mock)
    return repos_mock


def get_namespace_mock(namespace):
    namespace_mock = Mock()
    namespace_mock.repositories = Mock(side_effect=get_repositories_mock)
    return namespace_mock


def get_repo(namespace, name):
    return {
        "owner": namespace,
        "logo": "avatarurl",
        "slug": name,
        "description": "some %s repo" % (name),
        "utc_last_updated": str(datetime.utcfromtimestamp(0)),
        "read_only": namespace != "knownuser",
        "is_private": name == "somerepo",
    }


def get_visible_repos():
    repos = [
        get_repo("knownuser", "somerepo"),
        get_repo("someorg", "somerepo"),
        get_repo("someorg", "anotherrepo"),
    ]
    return (True, repos, None)


def get_authed_mock(token, secret):
    authed_mock = Mock()
    authed_mock.for_namespace = Mock(side_effect=get_namespace_mock)
    authed_mock.get_visible_repositories = Mock(side_effect=get_visible_repos)
    return authed_mock


def get_mock_bitbucket():
    bitbucket_mock = Mock()
    bitbucket_mock.get_authorized_client = Mock(side_effect=get_authed_mock)
    return bitbucket_mock
