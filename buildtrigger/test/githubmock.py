from datetime import datetime
from mock import Mock

from github import GithubException

from buildtrigger.githubhandler import GithubBuildTrigger
from util.morecollections import AttrDict


def get_github_trigger(dockerfile_path=""):
    trigger_obj = AttrDict(dict(auth_token="foobar", id="sometrigger"))
    trigger = GithubBuildTrigger(
        trigger_obj, {"build_source": "foo", "dockerfile_path": dockerfile_path}
    )
    trigger._get_client = get_mock_github
    return trigger


def get_mock_github():
    def get_commit_mock(commit_sha):
        if commit_sha == "aaaaaaa":
            commit_mock = Mock()
            commit_mock.sha = commit_sha
            commit_mock.html_url = "http://url/to/commit"
            commit_mock.last_modified = "now"

            commit_mock.commit = Mock()
            commit_mock.commit.message = "some cool message"

            commit_mock.committer = Mock()
            commit_mock.committer.login = "someuser"
            commit_mock.committer.avatar_url = "avatarurl"
            commit_mock.committer.html_url = "htmlurl"

            commit_mock.author = Mock()
            commit_mock.author.login = "someuser"
            commit_mock.author.avatar_url = "avatarurl"
            commit_mock.author.html_url = "htmlurl"
            return commit_mock

        raise GithubException(None, None)

    def get_branch_mock(branch_name):
        if branch_name == "master":
            branch_mock = Mock()
            branch_mock.commit = Mock()
            branch_mock.commit.sha = "aaaaaaa"
            return branch_mock

        raise GithubException(None, None)

    def get_repo_mock(namespace, name):
        repo_mock = Mock()
        repo_mock.owner = Mock()
        repo_mock.owner.login = namespace

        repo_mock.full_name = "%s/%s" % (namespace, name)
        repo_mock.name = name
        repo_mock.description = "some %s repo" % (name)

        if name != "anotherrepo":
            repo_mock.pushed_at = datetime.utcfromtimestamp(0)
        else:
            repo_mock.pushed_at = None

        repo_mock.html_url = "https://bitbucket.org/%s/%s" % (namespace, name)
        repo_mock.private = name == "somerepo"
        repo_mock.permissions = Mock()
        repo_mock.permissions.admin = namespace == "knownuser"
        return repo_mock

    def get_user_repos_mock(type="all", sort="created"):
        return [get_repo_mock("knownuser", "somerepo")]

    def get_org_repos_mock(type="all"):
        return [get_repo_mock("someorg", "somerepo"), get_repo_mock("someorg", "anotherrepo")]

    def get_orgs_mock():
        return [get_org_mock("someorg")]

    def get_user_mock(username="knownuser"):
        if username == "knownuser":
            user_mock = Mock()
            user_mock.name = username
            user_mock.plan = Mock()
            user_mock.plan.private_repos = 1
            user_mock.login = username
            user_mock.html_url = "https://bitbucket.org/%s" % (username)
            user_mock.avatar_url = "avatarurl"
            user_mock.get_repos = Mock(side_effect=get_user_repos_mock)
            user_mock.get_orgs = Mock(side_effect=get_orgs_mock)
            return user_mock

        raise GithubException(None, None)

    def get_org_mock(namespace):
        if namespace == "someorg":
            org_mock = Mock()
            org_mock.get_repos = Mock(side_effect=get_org_repos_mock)
            org_mock.login = namespace
            org_mock.html_url = "https://bitbucket.org/%s" % (namespace)
            org_mock.avatar_url = "avatarurl"
            org_mock.name = namespace
            org_mock.plan = Mock()
            org_mock.plan.private_repos = 2
            return org_mock

        raise GithubException(None, None)

    def get_tags_mock():
        sometag = Mock()
        sometag.name = "sometag"
        sometag.commit = get_commit_mock("aaaaaaa")

        someothertag = Mock()
        someothertag.name = "someothertag"
        someothertag.commit = get_commit_mock("aaaaaaa")
        return [sometag, someothertag]

    def get_branches_mock():
        master = Mock()
        master.name = "master"
        master.commit = get_commit_mock("aaaaaaa")

        otherbranch = Mock()
        otherbranch.name = "otherbranch"
        otherbranch.commit = get_commit_mock("aaaaaaa")
        return [master, otherbranch]

    def get_contents_mock(filepath):
        if filepath == "Dockerfile":
            m = Mock()
            m.content = "hello world"
            return m

        if filepath == "somesubdir/Dockerfile":
            m = Mock()
            m.content = "hi universe"
            return m

        raise GithubException(None, None)

    def get_git_tree_mock(commit_sha, recursive=False):
        first_file = Mock()
        first_file.type = "blob"
        first_file.path = "Dockerfile"

        second_file = Mock()
        second_file.type = "other"
        second_file.path = "/some/Dockerfile"

        third_file = Mock()
        third_file.type = "blob"
        third_file.path = "somesubdir/Dockerfile"

        t = Mock()

        if commit_sha == "aaaaaaa":
            t.tree = [
                first_file,
                second_file,
                third_file,
            ]
        else:
            t.tree = []

        return t

    repo_mock = Mock()
    repo_mock.default_branch = "master"
    repo_mock.ssh_url = "ssh_url"

    repo_mock.get_branch = Mock(side_effect=get_branch_mock)
    repo_mock.get_tags = Mock(side_effect=get_tags_mock)
    repo_mock.get_branches = Mock(side_effect=get_branches_mock)
    repo_mock.get_commit = Mock(side_effect=get_commit_mock)
    repo_mock.get_contents = Mock(side_effect=get_contents_mock)
    repo_mock.get_git_tree = Mock(side_effect=get_git_tree_mock)

    gh_mock = Mock()
    gh_mock.get_repo = Mock(return_value=repo_mock)
    gh_mock.get_user = Mock(side_effect=get_user_mock)
    gh_mock.get_organization = Mock(side_effect=get_org_mock)
    return gh_mock
