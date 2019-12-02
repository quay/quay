import pytest

from image.appc import DockerV1ToACIManifestTranslator
from util.dict_wrappers import JSONPathDict


EXAMPLE_MANIFEST_OBJ = {
    "architecture": "amd64",
    "config": {
        "Hostname": "1d811a9194c4",
        "Domainname": "",
        "User": "",
        "AttachStdin": False,
        "AttachStdout": False,
        "AttachStderr": False,
        "ExposedPorts": {"2379/tcp": {}, "2380/tcp": {}},
        "Tty": False,
        "OpenStdin": False,
        "StdinOnce": False,
        "Env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
        "Cmd": ["/usr/local/bin/etcd"],
        "ArgsEscaped": True,
        "Image": "sha256:4c86d1f362d42420c137846fae31667ee85ce6f2cab406cdff26a8ff8a2c31c4",
        "Volumes": None,
        "WorkingDir": "",
        "Entrypoint": None,
        "OnBuild": [],
        "Labels": {},
    },
    "container": "5a3565ce9b808a0eb0bcbc966dad624f76ad308ad24e11525b5da1201a1df135",
    "container_config": {
        "Hostname": "1d811a9194c4",
        "Domainname": "",
        "User": "",
        "AttachStdin": False,
        "AttachStdout": False,
        "AttachStderr": False,
        "ExposedPorts": {"2379/tcp": {}, "2380/tcp": {}},
        "Tty": False,
        "OpenStdin": False,
        "StdinOnce": False,
        "Env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
        "Cmd": ["/bin/sh", "-c", '#(nop) CMD ["/usr/local/bin/etcd"]'],
        "ArgsEscaped": True,
        "Image": "sha256:4c86d1f362d42420c137846fae31667ee85ce6f2cab406cdff26a8ff8a2c31c4",
        "Volumes": None,
        "WorkingDir": "",
        "Entrypoint": None,
        "OnBuild": [],
        "Labels": {},
    },
    "created": "2016-11-11T19:03:55.137387628Z",
    "docker_version": "1.11.1",
    "id": "3314a3781a526fe728e2e96cfcfb3cc0de901b5c102e6204e8b0155c8f7d5fd2",
    "os": "linux",
    "parent": "625342ec4d0f3d7a96fd3bb1ef0b4b0b6bc65ebb3d252fd33af0691f7984440e",
    "throwaway": True,
}


@pytest.mark.parametrize(
    "vcfg,expected",
    [
        ({"Volumes": None}, []),
        ({"Volumes": {}}, []),
        ({"Volumes": {"/bin": {}}}, [{"name": "volume-bin", "path": "/bin", "readOnly": False}]),
        ({"volumes": None}, []),
        ({"volumes": {}}, []),
        ({"volumes": {"/bin": {}}}, [{"name": "volume-bin", "path": "/bin", "readOnly": False}]),
    ],
)
def test_volume_version_easy(vcfg, expected):
    output = DockerV1ToACIManifestTranslator._build_volumes(JSONPathDict(vcfg))
    assert output == expected
