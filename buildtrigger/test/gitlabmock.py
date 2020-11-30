import base64
import json

from contextlib import contextmanager

import gitlab

from httmock import urlmatch, HTTMock

from buildtrigger.gitlabhandler import GitLabBuildTrigger
from util.morecollections import AttrDict


@urlmatch(netloc=r"fakegitlab")
def catchall_handler(url, request):
    return {"status_code": 404}


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/users$")
def users_handler(url, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    if url.query.find("knownuser") < 0:
        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps([]),
        }

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            [
                {
                    "id": 1,
                    "username": "knownuser",
                    "name": "Known User",
                    "state": "active",
                    "avatar_url": "avatarurl",
                    "web_url": "https://bitbucket.org/knownuser",
                },
            ]
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/user$")
def user_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": 1,
                "username": "john_smith",
                "email": "john@example.com",
                "name": "John Smith",
                "state": "active",
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/foo%2Fbar$")
def project_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": 4,
                "description": None,
                "default_branch": "master",
                "visibility": "private",
                "path_with_namespace": "someorg/somerepo",
                "ssh_url_to_repo": "git@example.com:someorg/somerepo.git",
                "web_url": "http://example.com/someorg/somerepo",
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/tree$")
def project_tree_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            [
                {
                    "id": "a1e8f8d745cc87e3a9248358d9352bb7f9a0aeba",
                    "name": "Dockerfile",
                    "type": "tree",
                    "path": "files/Dockerfile",
                    "mode": "040000",
                },
            ]
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/tags$")
def project_tags_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            [
                {
                    "name": "sometag",
                    "commit": {
                        "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                    },
                },
                {
                    "name": "someothertag",
                    "commit": {
                        "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                    },
                },
            ]
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/branches$")
def project_branches_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            [
                {
                    "name": "master",
                    "commit": {
                        "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                    },
                },
                {
                    "name": "otherbranch",
                    "commit": {
                        "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                    },
                },
            ]
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/branches/master$")
def project_branch_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "name": "master",
                "merged": True,
                "protected": True,
                "developers_can_push": False,
                "developers_can_merge": False,
                "commit": {
                    "author_email": "john@example.com",
                    "author_name": "John Smith",
                    "authored_date": "2012-06-27T05:51:39-07:00",
                    "committed_date": "2012-06-28T03:44:20-07:00",
                    "committer_email": "john@example.com",
                    "committer_name": "John Smith",
                    "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                    "short_id": "7b5c3cc",
                    "title": "add projects API",
                    "message": "add projects API",
                    "parent_ids": [
                        "4ad91d3c1144c406e50c7b33bae684bd6837faf8",
                    ],
                },
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/namespaces/someorg$")
def namespace_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": 2,
                "name": "someorg",
                "path": "someorg",
                "kind": "group",
                "full_path": "someorg",
                "parent_id": None,
                "members_count_with_descendants": 2,
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/namespaces/knownuser$")
def user_namespace_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": 1,
                "name": "knownuser",
                "path": "knownuser",
                "kind": "user",
                "full_path": "knownuser",
                "parent_id": None,
                "members_count_with_descendants": 2,
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/namespaces(/)?$")
def namespaces_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            [
                {
                    "id": 2,
                    "name": "someorg",
                    "path": "someorg",
                    "kind": "group",
                    "full_path": "someorg",
                    "parent_id": None,
                    "web_url": "http://gitlab.com/groups/someorg",
                    "members_count_with_descendants": 2,
                }
            ]
        ),
    }


def get_projects_handler(add_permissions_block):
    @urlmatch(netloc=r"fakegitlab", path=r"/api/v4/groups/2/projects$")
    def projects_handler(_, request):
        if not request.headers.get("Authorization") == "Bearer foobar":
            return {"status_code": 401}

        permissions_block = {
            "project_access": {"access_level": 10, "notification_level": 3},
            "group_access": {"access_level": 20, "notification_level": 3},
        }

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps(
                [
                    {
                        "id": 4,
                        "name": "Some project",
                        "description": None,
                        "default_branch": "master",
                        "visibility": "private",
                        "path": "someproject",
                        "path_with_namespace": "someorg/someproject",
                        "last_activity_at": "2013-09-30T13:46:02Z",
                        "web_url": "http://example.com/someorg/someproject",
                        "permissions": permissions_block if add_permissions_block else None,
                    },
                    {
                        "id": 5,
                        "name": "Another project",
                        "description": None,
                        "default_branch": "master",
                        "visibility": "public",
                        "path": "anotherproject",
                        "path_with_namespace": "someorg/anotherproject",
                        "last_activity_at": "2013-09-30T13:46:02Z",
                        "web_url": "http://example.com/someorg/anotherproject",
                    },
                ]
            ),
        }

    return projects_handler


def get_group_handler(null_avatar):
    @urlmatch(netloc=r"fakegitlab", path=r"/api/v4/groups/2$")
    def group_handler(_, request):
        if not request.headers.get("Authorization") == "Bearer foobar":
            return {"status_code": 401}

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps(
                {
                    "id": 1,
                    "name": "SomeOrg Group",
                    "path": "someorg",
                    "description": "An interesting group",
                    "visibility": "public",
                    "lfs_enabled": True,
                    "avatar_url": "avatar_url" if not null_avatar else None,
                    "web_url": "http://gitlab.com/groups/someorg",
                    "request_access_enabled": False,
                    "full_name": "SomeOrg Group",
                    "full_path": "someorg",
                    "parent_id": None,
                }
            ),
        }

    return group_handler


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/files/Dockerfile$")
def dockerfile_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "file_name": "Dockerfile",
                "file_path": "Dockerfile",
                "size": 10,
                "encoding": "base64",
                "content": base64.b64encode(b"hello world").decode("ascii"),
                "ref": "master",
                "blob_id": "79f7bbd25901e8334750839545a9bd021f0e4c83",
                "commit_id": "d5a3ff139356ce33e37e73add446f16869741b50",
                "last_commit_id": "570e7b2abdd848b95f2f578043fc23bd6f6fd24d",
            }
        ),
    }


@urlmatch(
    netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/files/somesubdir%2FDockerfile$"
)
def sub_dockerfile_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "file_name": "Dockerfile",
                "file_path": "somesubdir/Dockerfile",
                "size": 10,
                "encoding": "base64",
                "content": base64.b64encode(b"hi universe").decode("ascii"),
                "ref": "master",
                "blob_id": "79f7bbd25901e8334750839545a9bd021f0e4c83",
                "commit_id": "d5a3ff139356ce33e37e73add446f16869741b50",
                "last_commit_id": "570e7b2abdd848b95f2f578043fc23bd6f6fd24d",
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/repository/tags/sometag$")
def tag_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "name": "sometag",
                "message": "some cool message",
                "target": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                "commit": {
                    "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                    "short_id": "60a8ff03",
                    "title": "Initial commit",
                    "created_at": "2017-07-26T11:08:53.000+02:00",
                    "parent_ids": ["f61c062ff8bcbdb00e0a1b3317a91aed6ceee06b"],
                    "message": "v5.0.0\n",
                    "author_name": "Arthur Verschaeve",
                    "author_email": "contact@arthurverschaeve.be",
                    "authored_date": "2015-02-01T21:56:31.000+01:00",
                    "committer_name": "Arthur Verschaeve",
                    "committer_email": "contact@arthurverschaeve.be",
                    "committed_date": "2015-02-01T21:56:31.000+01:00",
                },
                "release": None,
            }
        ),
    }


@urlmatch(
    netloc=r"fakegitlab",
    path=r"/api/v4/projects/foo%2Fbar/repository/commits/60a8ff033665e1207714d6670fcd7b65304ec02f$",
)
def commit_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": "60a8ff033665e1207714d6670fcd7b65304ec02f",
                "short_id": "60a8ff03366",
                "title": "Sanitize for network graph",
                "author_name": "someguy",
                "author_email": "some.guy@gmail.com",
                "committer_name": "Some Guy",
                "committer_email": "some.guy@gmail.com",
                "created_at": "2012-09-20T09:06:12+03:00",
                "message": "Sanitize for network graph",
                "committed_date": "2012-09-20T09:06:12+03:00",
                "authored_date": "2012-09-20T09:06:12+03:00",
                "parent_ids": ["ae1d9fb46aa2b07ee9836d49862ec4e2c46fbbba"],
                "last_pipeline": {
                    "id": 8,
                    "ref": "master",
                    "sha": "2dc6aa325a317eda67812f05600bdf0fcdc70ab0",
                    "status": "created",
                },
                "stats": {"additions": 15, "deletions": 10, "total": 25},
                "status": "running",
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/deploy_keys$", method="POST")
def create_deploykey_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": 1,
                "title": "Public key",
                "key": "ssh-rsa some stuff",
                "created_at": "2013-10-02T10:12:29Z",
                "can_push": False,
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/hooks$", method="POST")
def create_hook_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            {
                "id": 1,
                "url": "http://example.com/hook",
                "project_id": 4,
                "push_events": True,
                "issues_events": True,
                "confidential_issues_events": True,
                "merge_requests_events": True,
                "tag_push_events": True,
                "note_events": True,
                "job_events": True,
                "pipeline_events": True,
                "wiki_page_events": True,
                "enable_ssl_verification": True,
                "created_at": "2012-10-12T17:04:47Z",
            }
        ),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/hooks/1$", method="DELETE")
def delete_hook_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps({}),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/projects/4/deploy_keys/1$", method="DELETE")
def delete_deploykey_handker(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps({}),
    }


@urlmatch(netloc=r"fakegitlab", path=r"/api/v4/users/1/projects$")
def user_projects_list_handler(_, request):
    if not request.headers.get("Authorization") == "Bearer foobar":
        return {"status_code": 401}

    return {
        "status_code": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "content": json.dumps(
            [
                {
                    "id": 2,
                    "name": "Another project",
                    "description": None,
                    "default_branch": "master",
                    "visibility": "public",
                    "path": "anotherproject",
                    "path_with_namespace": "knownuser/anotherproject",
                    "last_activity_at": "2013-09-30T13:46:02Z",
                    "web_url": "http://example.com/knownuser/anotherproject",
                }
            ]
        ),
    }


@contextmanager
def get_gitlab_trigger(dockerfile_path="", add_permissions=True, missing_avatar_url=False):
    handlers = [
        user_handler,
        users_handler,
        project_branches_handler,
        project_tree_handler,
        project_handler,
        get_projects_handler(add_permissions),
        tag_handler,
        project_branch_handler,
        get_group_handler(missing_avatar_url),
        dockerfile_handler,
        sub_dockerfile_handler,
        namespace_handler,
        user_namespace_handler,
        namespaces_handler,
        commit_handler,
        create_deploykey_handler,
        delete_deploykey_handker,
        create_hook_handler,
        delete_hook_handler,
        project_tags_handler,
        user_projects_list_handler,
        catchall_handler,
    ]

    with HTTMock(*handlers):
        trigger_obj = AttrDict(dict(auth_token="foobar", id="sometrigger"))
        trigger = GitLabBuildTrigger(
            trigger_obj,
            {
                "build_source": "foo/bar",
                "dockerfile_path": dockerfile_path,
                "username": "knownuser",
            },
        )

        client = gitlab.Gitlab("http://fakegitlab", oauth_token="foobar", timeout=20, api_version=4)
        client.auth()

        trigger._get_authorized_client = lambda: client
        yield trigger
