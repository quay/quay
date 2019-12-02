import json

import pytest

from jsonschema import validate

from buildtrigger.customhandler import custom_trigger_payload
from buildtrigger.basehandler import METADATA_SCHEMA
from buildtrigger.bitbuckethandler import get_transformed_webhook_payload as bb_webhook
from buildtrigger.bitbuckethandler import get_transformed_commit_info as bb_commit
from buildtrigger.githubhandler import get_transformed_webhook_payload as gh_webhook
from buildtrigger.gitlabhandler import get_transformed_webhook_payload as gl_webhook
from buildtrigger.triggerutil import SkipRequestException


def assertSkipped(filename, processor, *args, **kwargs):
    with open("buildtrigger/test/triggerjson/%s.json" % filename) as f:
        payload = json.loads(f.read())

    nargs = [payload]
    nargs.extend(args)

    with pytest.raises(SkipRequestException):
        processor(*nargs, **kwargs)


def assertSchema(filename, expected, processor, *args, **kwargs):
    with open("buildtrigger/test/triggerjson/%s.json" % filename) as f:
        payload = json.loads(f.read())

    nargs = [payload]
    nargs.extend(args)

    created = processor(*nargs, **kwargs)
    assert created == expected
    validate(created, METADATA_SCHEMA)


def test_custom_custom():
    expected = {
        u"commit": u"1c002dd",
        u"commit_info": {
            u"url": u"gitsoftware.com/repository/commits/1234567",
            u"date": u"timestamp",
            u"message": u"initial commit",
            u"committer": {
                u"username": u"user",
                u"url": u"gitsoftware.com/users/user",
                u"avatar_url": u"gravatar.com/user.png",
            },
            u"author": {
                u"username": u"user",
                u"url": u"gitsoftware.com/users/user",
                u"avatar_url": u"gravatar.com/user.png",
            },
        },
        u"ref": u"refs/heads/master",
        u"default_branch": u"master",
        u"git_url": u"foobar",
    }

    assertSchema("custom_webhook", expected, custom_trigger_payload, git_url="foobar")


def test_custom_gitlab():
    expected = {
        "commit": u"fb88379ee45de28a0a4590fddcbd8eff8b36026e",
        "ref": u"refs/heads/master",
        "git_url": u"git@gitlab.com:jsmith/somerepo.git",
        "commit_info": {
            "url": u"https://gitlab.com/jsmith/somerepo/commit/fb88379ee45de28a0a4590fddcbd8eff8b36026e",
            "date": u"2015-08-13T19:33:18+00:00",
            "message": u"Fix link\n",
        },
    }

    assertSchema(
        "gitlab_webhook",
        expected,
        custom_trigger_payload,
        git_url="git@gitlab.com:jsmith/somerepo.git",
    )


def test_custom_github():
    expected = {
        "commit": u"410f4cdf8ff09b87f245b13845e8497f90b90a4c",
        "ref": u"refs/heads/master",
        "default_branch": u"master",
        "git_url": u"git@github.com:jsmith/anothertest.git",
        "commit_info": {
            "url": u"https://github.com/jsmith/anothertest/commit/410f4cdf8ff09b87f245b13845e8497f90b90a4c",
            "date": u"2015-09-11T14:26:16-04:00",
            "message": u"Update Dockerfile",
            "committer": {"username": u"jsmith",},
            "author": {"username": u"jsmith",},
        },
    }

    assertSchema(
        "github_webhook",
        expected,
        custom_trigger_payload,
        git_url="git@github.com:jsmith/anothertest.git",
    )


def test_custom_bitbucket():
    expected = {
        "commit": u"af64ae7188685f8424040b4735ad12941b980d75",
        "ref": u"refs/heads/master",
        "git_url": u"git@bitbucket.org:jsmith/another-repo.git",
        "commit_info": {
            "url": u"https://bitbucket.org/jsmith/another-repo/commits/af64ae7188685f8424040b4735ad12941b980d75",
            "date": u"2015-09-10T20:40:54+00:00",
            "message": u"Dockerfile edited online with Bitbucket",
            "author": {
                "username": u"John Smith",
                "avatar_url": u"https://bitbucket.org/account/jsmith/avatar/32/",
            },
            "committer": {
                "username": u"John Smith",
                "avatar_url": u"https://bitbucket.org/account/jsmith/avatar/32/",
            },
        },
    }

    assertSchema(
        "bitbucket_webhook",
        expected,
        custom_trigger_payload,
        git_url="git@bitbucket.org:jsmith/another-repo.git",
    )


def test_bitbucket_customer_payload_noauthor():
    expected = {
        "commit": "a0ec139843b2bb281ab21a433266ddc498e605dc",
        "ref": "refs/heads/master",
        "git_url": "git@bitbucket.org:somecoollabs/svc-identity.git",
        "commit_info": {
            "url": "https://bitbucket.org/somecoollabs/svc-identity/commits/a0ec139843b2bb281ab21a433266ddc498e605dc",
            "date": "2015-09-25T00:55:08+00:00",
            "message": "Update version.py to 0.1.2 [skip ci]\n\n(by utilitybelt/scripts/autotag_version.py)\n",
            "committer": {
                "username": "CodeShip Tagging",
                "avatar_url": "https://bitbucket.org/account/SomeCoolLabs_CodeShip/avatar/32/",
            },
        },
    }

    assertSchema("bitbucket_customer_example_noauthor", expected, bb_webhook)


def test_bitbucket_customer_payload_tag():
    expected = {
        "commit": "a0ec139843b2bb281ab21a433266ddc498e605dc",
        "ref": "refs/tags/0.1.2",
        "git_url": "git@bitbucket.org:somecoollabs/svc-identity.git",
        "commit_info": {
            "url": "https://bitbucket.org/somecoollabs/svc-identity/commits/a0ec139843b2bb281ab21a433266ddc498e605dc",
            "date": "2015-09-25T00:55:08+00:00",
            "message": "Update version.py to 0.1.2 [skip ci]\n\n(by utilitybelt/scripts/autotag_version.py)\n",
            "committer": {
                "username": "CodeShip Tagging",
                "avatar_url": "https://bitbucket.org/account/SomeCoolLabs_CodeShip/avatar/32/",
            },
        },
    }

    assertSchema("bitbucket_customer_example_tag", expected, bb_webhook)


def test_bitbucket_commit():
    ref = "refs/heads/somebranch"
    default_branch = "somebranch"
    repository_name = "foo/bar"

    def lookup_author(_):
        return {"user": {"display_name": "cooluser", "avatar": "http://some/avatar/url"}}

    expected = {
        "commit": u"abdeaf1b2b4a6b9ddf742c1e1754236380435a62",
        "ref": u"refs/heads/somebranch",
        "git_url": u"git@bitbucket.org:foo/bar.git",
        "default_branch": u"somebranch",
        "commit_info": {
            "url": u"https://bitbucket.org/foo/bar/commits/abdeaf1b2b4a6b9ddf742c1e1754236380435a62",
            "date": u"2012-07-24 00:26:36",
            "message": u"making some changes\n",
            "author": {"avatar_url": u"http://some/avatar/url", "username": u"cooluser",},
        },
    }

    assertSchema(
        "bitbucket_commit", expected, bb_commit, ref, default_branch, repository_name, lookup_author
    )


def test_bitbucket_webhook_payload():
    expected = {
        "commit": u"af64ae7188685f8424040b4735ad12941b980d75",
        "ref": u"refs/heads/master",
        "git_url": u"git@bitbucket.org:jsmith/another-repo.git",
        "commit_info": {
            "url": u"https://bitbucket.org/jsmith/another-repo/commits/af64ae7188685f8424040b4735ad12941b980d75",
            "date": u"2015-09-10T20:40:54+00:00",
            "message": u"Dockerfile edited online with Bitbucket",
            "author": {
                "username": u"John Smith",
                "avatar_url": u"https://bitbucket.org/account/jsmith/avatar/32/",
            },
            "committer": {
                "username": u"John Smith",
                "avatar_url": u"https://bitbucket.org/account/jsmith/avatar/32/",
            },
        },
    }

    assertSchema("bitbucket_webhook", expected, bb_webhook)


def test_github_webhook_payload_slash_branch():
    expected = {
        "commit": u"410f4cdf8ff09b87f245b13845e8497f90b90a4c",
        "ref": u"refs/heads/slash/branch",
        "default_branch": u"master",
        "git_url": u"git@github.com:jsmith/anothertest.git",
        "commit_info": {
            "url": u"https://github.com/jsmith/anothertest/commit/410f4cdf8ff09b87f245b13845e8497f90b90a4c",
            "date": u"2015-09-11T14:26:16-04:00",
            "message": u"Update Dockerfile",
            "committer": {"username": u"jsmith",},
            "author": {"username": u"jsmith",},
        },
    }

    assertSchema("github_webhook_slash_branch", expected, gh_webhook)


def test_github_webhook_payload():
    expected = {
        "commit": u"410f4cdf8ff09b87f245b13845e8497f90b90a4c",
        "ref": u"refs/heads/master",
        "default_branch": u"master",
        "git_url": u"git@github.com:jsmith/anothertest.git",
        "commit_info": {
            "url": u"https://github.com/jsmith/anothertest/commit/410f4cdf8ff09b87f245b13845e8497f90b90a4c",
            "date": u"2015-09-11T14:26:16-04:00",
            "message": u"Update Dockerfile",
            "committer": {"username": u"jsmith",},
            "author": {"username": u"jsmith",},
        },
    }

    assertSchema("github_webhook", expected, gh_webhook)


def test_github_webhook_payload_with_lookup():
    expected = {
        "commit": u"410f4cdf8ff09b87f245b13845e8497f90b90a4c",
        "ref": u"refs/heads/master",
        "default_branch": u"master",
        "git_url": u"git@github.com:jsmith/anothertest.git",
        "commit_info": {
            "url": u"https://github.com/jsmith/anothertest/commit/410f4cdf8ff09b87f245b13845e8497f90b90a4c",
            "date": u"2015-09-11T14:26:16-04:00",
            "message": u"Update Dockerfile",
            "committer": {
                "username": u"jsmith",
                "url": u"http://github.com/jsmith",
                "avatar_url": u"http://some/avatar/url",
            },
            "author": {
                "username": u"jsmith",
                "url": u"http://github.com/jsmith",
                "avatar_url": u"http://some/avatar/url",
            },
        },
    }

    def lookup_user(_):
        return {"html_url": "http://github.com/jsmith", "avatar_url": "http://some/avatar/url"}

    assertSchema("github_webhook", expected, gh_webhook, lookup_user=lookup_user)


def test_github_webhook_payload_missing_fields_with_lookup():
    expected = {
        "commit": u"410f4cdf8ff09b87f245b13845e8497f90b90a4c",
        "ref": u"refs/heads/master",
        "default_branch": u"master",
        "git_url": u"git@github.com:jsmith/anothertest.git",
        "commit_info": {
            "url": u"https://github.com/jsmith/anothertest/commit/410f4cdf8ff09b87f245b13845e8497f90b90a4c",
            "date": u"2015-09-11T14:26:16-04:00",
            "message": u"Update Dockerfile",
        },
    }

    def lookup_user(username):
        if not username:
            raise Exception("Fail!")

        return {"html_url": "http://github.com/jsmith", "avatar_url": "http://some/avatar/url"}

    assertSchema("github_webhook_missing", expected, gh_webhook, lookup_user=lookup_user)


def test_gitlab_webhook_payload():
    expected = {
        "commit": u"fb88379ee45de28a0a4590fddcbd8eff8b36026e",
        "ref": u"refs/heads/master",
        "git_url": u"git@gitlab.com:jsmith/somerepo.git",
        "commit_info": {
            "url": u"https://gitlab.com/jsmith/somerepo/commit/fb88379ee45de28a0a4590fddcbd8eff8b36026e",
            "date": u"2015-08-13T19:33:18+00:00",
            "message": u"Fix link\n",
        },
    }

    assertSchema("gitlab_webhook", expected, gl_webhook)


def test_github_webhook_payload_known_issue():
    expected = {
        "commit": "118b07121695d9f2e40a5ff264fdcc2917680870",
        "ref": "refs/heads/master",
        "default_branch": "master",
        "git_url": "git@github.com:jsmith/docker-test.git",
        "commit_info": {
            "url": "https://github.com/jsmith/docker-test/commit/118b07121695d9f2e40a5ff264fdcc2917680870",
            "date": "2015-09-25T14:55:11-04:00",
            "message": "Fail",
        },
    }

    assertSchema("github_webhook_noname", expected, gh_webhook)


def test_github_webhook_payload_missing_fields():
    expected = {
        "commit": u"410f4cdf8ff09b87f245b13845e8497f90b90a4c",
        "ref": u"refs/heads/master",
        "default_branch": u"master",
        "git_url": u"git@github.com:jsmith/anothertest.git",
        "commit_info": {
            "url": u"https://github.com/jsmith/anothertest/commit/410f4cdf8ff09b87f245b13845e8497f90b90a4c",
            "date": u"2015-09-11T14:26:16-04:00",
            "message": u"Update Dockerfile",
        },
    }

    assertSchema("github_webhook_missing", expected, gh_webhook)


def test_gitlab_webhook_nocommit_payload():
    assertSkipped("gitlab_webhook_nocommit", gl_webhook)


def test_gitlab_webhook_multiple_commits():
    expected = {
        "commit": u"9a052a0b2fbe01d4a1a88638dd9fe31c1c56ef53",
        "ref": u"refs/heads/master",
        "git_url": u"git@gitlab.com:jsmith/some-test-project.git",
        "commit_info": {
            "url": u"https://gitlab.com/jsmith/some-test-project/commit/9a052a0b2fbe01d4a1a88638dd9fe31c1c56ef53",
            "date": u"2016-09-29T15:02:41+00:00",
            "message": u"Merge branch 'foobar' into 'master'\r\n\r\nAdd changelog\r\n\r\nSome merge thing\r\n\r\nSee merge request !1",
            "author": {
                "username": "jsmith",
                "url": "http://gitlab.com/jsmith",
                "avatar_url": "http://some/avatar/url",
            },
        },
    }

    def lookup_user(_):
        return {
            "username": "jsmith",
            "html_url": "http://gitlab.com/jsmith",
            "avatar_url": "http://some/avatar/url",
        }

    assertSchema("gitlab_webhook_multicommit", expected, gl_webhook, lookup_user=lookup_user)


def test_gitlab_webhook_for_tag():
    expected = {
        "commit": u"82b3d5ae55f7080f1e6022629cdb57bfae7cccc7",
        "commit_info": {
            "author": {
                "avatar_url": "http://some/avatar/url",
                "url": "http://gitlab.com/jsmith",
                "username": "jsmith",
            },
            "date": "2015-08-13T19:33:18+00:00",
            "message": "Fix link\n",
            "url": "https://some/url",
        },
        "git_url": u"git@example.com:jsmith/example.git",
        "ref": u"refs/tags/v1.0.0",
    }

    def lookup_user(_):
        return {
            "username": "jsmith",
            "html_url": "http://gitlab.com/jsmith",
            "avatar_url": "http://some/avatar/url",
        }

    def lookup_commit(repo_id, commit_sha):
        if commit_sha == "82b3d5ae55f7080f1e6022629cdb57bfae7cccc7":
            return {
                "id": "82b3d5ae55f7080f1e6022629cdb57bfae7cccc7",
                "message": "Fix link\n",
                "timestamp": "2015-08-13T19:33:18+00:00",
                "url": "https://some/url",
                "author_name": "Foo Guy",
                "author_email": "foo@bar.com",
            }

        return None

    assertSchema(
        "gitlab_webhook_tag",
        expected,
        gl_webhook,
        lookup_user=lookup_user,
        lookup_commit=lookup_commit,
    )


def test_gitlab_webhook_for_tag_nocommit():
    assertSkipped("gitlab_webhook_tag", gl_webhook)


def test_gitlab_webhook_for_tag_commit_sha_null():
    assertSkipped("gitlab_webhook_tag_commit_sha_null", gl_webhook)


def test_gitlab_webhook_for_tag_known_issue():
    expected = {
        "commit": u"770830e7ca132856991e6db4f7fc0f4dbe20bd5f",
        "ref": u"refs/tags/thirdtag",
        "git_url": u"git@gitlab.com:someuser/some-test-project.git",
        "commit_info": {
            "url": u"https://gitlab.com/someuser/some-test-project/commit/770830e7ca132856991e6db4f7fc0f4dbe20bd5f",
            "date": u"2019-10-17T18:07:48Z",
            "message": u"Update Dockerfile",
            "author": {
                "username": "someuser",
                "url": "http://gitlab.com/someuser",
                "avatar_url": "http://some/avatar/url",
            },
        },
    }

    def lookup_user(_):
        return {
            "username": "someuser",
            "html_url": "http://gitlab.com/someuser",
            "avatar_url": "http://some/avatar/url",
        }

    assertSchema("gitlab_webhook_tag_commit_issue", expected, gl_webhook, lookup_user=lookup_user)


def test_gitlab_webhook_payload_known_issue():
    expected = {
        "commit": u"770830e7ca132856991e6db4f7fc0f4dbe20bd5f",
        "ref": u"refs/tags/fourthtag",
        "git_url": u"git@gitlab.com:someuser/some-test-project.git",
        "commit_info": {
            "url": u"https://gitlab.com/someuser/some-test-project/commit/770830e7ca132856991e6db4f7fc0f4dbe20bd5f",
            "date": u"2019-10-17T18:07:48Z",
            "message": u"Update Dockerfile",
        },
    }

    def lookup_commit(repo_id, commit_sha):
        if commit_sha == "770830e7ca132856991e6db4f7fc0f4dbe20bd5f":
            return {
                "added": [],
                "author": {"name": "Some User", "email": "someuser@somedomain.com"},
                "url": "https://gitlab.com/someuser/some-test-project/commit/770830e7ca132856991e6db4f7fc0f4dbe20bd5f",
                "message": "Update Dockerfile",
                "removed": [],
                "modified": ["Dockerfile"],
                "id": "770830e7ca132856991e6db4f7fc0f4dbe20bd5f",
            }

        return None

    assertSchema("gitlab_webhook_known_issue", expected, gl_webhook, lookup_commit=lookup_commit)


def test_gitlab_webhook_for_other():
    assertSkipped("gitlab_webhook_other", gl_webhook)


def test_gitlab_webhook_payload_with_lookup():
    expected = {
        "commit": u"fb88379ee45de28a0a4590fddcbd8eff8b36026e",
        "ref": u"refs/heads/master",
        "git_url": u"git@gitlab.com:jsmith/somerepo.git",
        "commit_info": {
            "url": u"https://gitlab.com/jsmith/somerepo/commit/fb88379ee45de28a0a4590fddcbd8eff8b36026e",
            "date": u"2015-08-13T19:33:18+00:00",
            "message": u"Fix link\n",
            "author": {
                "username": "jsmith",
                "url": "http://gitlab.com/jsmith",
                "avatar_url": "http://some/avatar/url",
            },
        },
    }

    def lookup_user(_):
        return {
            "username": "jsmith",
            "html_url": "http://gitlab.com/jsmith",
            "avatar_url": "http://some/avatar/url",
        }

    assertSchema("gitlab_webhook", expected, gl_webhook, lookup_user=lookup_user)


def test_github_webhook_payload_deleted_commit():
    expected = {
        "commit": u"456806b662cb903a0febbaed8344f3ed42f27bab",
        "commit_info": {
            "author": {"username": u"jsmith"},
            "committer": {"username": u"jsmith"},
            "date": u"2015-12-08T18:07:03-05:00",
            "message": (
                u"Merge pull request #1044 from jsmith/errerror\n\n"
                + "Assign the exception to a variable to log it"
            ),
            "url": u"https://github.com/jsmith/somerepo/commit/456806b662cb903a0febbaed8344f3ed42f27bab",
        },
        "git_url": u"git@github.com:jsmith/somerepo.git",
        "ref": u"refs/heads/master",
        "default_branch": u"master",
    }

    def lookup_user(_):
        return None

    assertSchema("github_webhook_deletedcommit", expected, gh_webhook, lookup_user=lookup_user)


def test_github_webhook_known_issue():
    def lookup_user(_):
        return None

    assertSkipped("github_webhook_knownissue", gh_webhook, lookup_user=lookup_user)


def test_bitbucket_webhook_known_issue():
    assertSkipped("bitbucket_knownissue", bb_webhook)
