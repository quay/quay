import json
import pytest

from image.docker.schema2.config import MalformedSchema2Config, DockerSchema2Config
from util.bytes import Bytes


@pytest.mark.parametrize(
    "json_data",
    [
        "",
        "{}",
        """
  {
    "unknown": "key"
  }
  """,
    ],
)
def test_malformed_configs(json_data):
    with pytest.raises(MalformedSchema2Config):
        DockerSchema2Config(Bytes.for_string_or_unicode(json_data))


CONFIG_BYTES = json.dumps(
    {
        "architecture": "amd64",
        "config": {
            "Hostname": "",
            "Domainname": "",
            "User": "",
            "AttachStdin": False,
            "AttachStdout": False,
            "AttachStderr": False,
            "Tty": False,
            "OpenStdin": False,
            "StdinOnce": False,
            "Env": [
                "HTTP_PROXY=http:\/\/localhost:8080",
                "http_proxy=http:\/\/localhost:8080",
                "PATH=\/usr\/local\/sbin:\/usr\/local\/bin:\/usr\/sbin:\/usr\/bin:\/sbin:\/bin",
            ],
            "Cmd": ["sh"],
            "Image": "",
            "Volumes": None,
            "WorkingDir": "",
            "Entrypoint": None,
            "OnBuild": None,
            "Labels": {},
        },
        "container": "b7a43694b435c8e9932615643f61f975a9213e453b15cd6c2a386f144a2d2de9",
        "container_config": {
            "Hostname": "b7a43694b435",
            "Domainname": "",
            "User": "",
            "AttachStdin": True,
            "AttachStdout": True,
            "AttachStderr": True,
            "Tty": True,
            "OpenStdin": True,
            "StdinOnce": True,
            "Env": [
                "HTTP_PROXY=http:\/\/localhost:8080",
                "http_proxy=http:\/\/localhost:8080",
                "PATH=\/usr\/local\/sbin:\/usr\/local\/bin:\/usr\/sbin:\/usr\/bin:\/sbin:\/bin",
            ],
            "Cmd": ["sh"],
            "Image": "jschorr\/somerepo",
            "Volumes": None,
            "WorkingDir": "",
            "Entrypoint": None,
            "OnBuild": None,
            "Labels": {},
        },
        "created": "2018-04-16T10:41:19.079522722Z",
        "docker_version": "17.09.0-ce",
        "history": [
            {
                "created": "2018-04-03T18:37:09.284840891Z",
                "created_by": "\/bin\/sh -c #(nop) ADD file:9e4ca21cbd24dc05b454b6be21c7c639216ae66559b21ba24af0d665c62620dc in \/ ",
            },
            {
                "created": "2018-04-03T18:37:09.613317719Z",
                "created_by": '/bin/sh -c #(nop)  CMD ["sh"]',
                "empty_layer": True,
            },
            {"created": "2018-04-16T10:37:44.418262777Z", "created_by": "sh"},
            {"created": "2018-04-16T10:41:19.079522722Z", "created_by": "sh"},
        ],
        "os": "linux",
        "rootfs": {
            "type": "layers",
            "diff_ids": [
                "sha256:3e596351c689c8827a3c9635bc1083cff17fa4a174f84f0584bd0ae6f384195b",
                "sha256:4552be273c71275a88de0b8c8853dcac18cb74d5790f5383d9b38d4ac55062d5",
                "sha256:1319c76152ca37fbeb7fb71e0ffa7239bc19ffbe3b95c00417ece39d89d06e6e",
            ],
        },
    }
)


def test_valid_config():
    config = DockerSchema2Config(Bytes.for_string_or_unicode(CONFIG_BYTES))
    history = list(config.history)
    assert len(history) == 4

    assert not history[0].is_empty
    assert history[1].is_empty

    assert history[0].created_datetime.year == 2018
    assert history[1].command == '/bin/sh -c #(nop)  CMD ["sh"]'
    assert history[2].command == "sh"

    for index, history_entry in enumerate(history):
        v1_compat = config.build_v1_compatibility(
            history_entry, "somev1id", "someparentid", index == 3
        )
        assert v1_compat["id"] == "somev1id"
        assert v1_compat["parent"] == "someparentid"

        if index == 3:
            assert v1_compat["container_config"] == config._parsed["container_config"]
        else:
            assert "Hostname" not in v1_compat["container_config"]
            assert v1_compat["container_config"]["Cmd"] == [history_entry.command]

    assert config.labels == {}
