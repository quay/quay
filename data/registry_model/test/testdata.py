from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)

# docker.io/library/python:bullseye
PYTHON_BULLSEYE = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:90213d7c778e0c59de4420925fc35ff76d8d91f6b0ddcf16789af05b78ddc779",
    "manifest": '{"manifests":[{"digest":"sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":2218},{"digest":"sha256:7f2fa3897549ad7a3b64353c5f7bf61021d22ec4073137804660d1aa3b3143ac","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":2218},{"digest":"sha256:4dd7b7c5bfc1ca08ddd4b0707278afc4859ff879438c4835b3cec7eb5e85a9ee","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":2218},{"digest":"sha256:80f1f8bcde1cf3b5b9a6b1ade3c90233f2738f5c0685685bdcccde311530caa8","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":2218},{"digest":"sha256:f501c3f975948f1ee60a5261efbb156abbcdd01c193bae1bbcffa6a2f2d8cb5d","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":2218},{"digest":"sha256:4f5c4c677c87e98f00b8affef87651f65c258c9b4b53ba4b237ac7f7668cac4e","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":2218},{"digest":"sha256:f3fb8be68a0eb71df0c54c0b8cb7aa192934ac7becb4cf2ac4142c925c3cbfdd","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":2218},{"digest":"sha256:969d7a3a04292e2f54c79f24f56ad520e4b355eaa2066420b63928337c22109d","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":2218}],"mediaType":"application\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}',
}

# docker.io/library/python:latest
PYTHON_LATEST = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:567018293e51a89db96ce4c9679fdefc89b3d17a9fe9e94c0091b04ac5bb4e89",
    "manifest": '{"manifests":[{"digest":"sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":2218},{"digest":"sha256:7f2fa3897549ad7a3b64353c5f7bf61021d22ec4073137804660d1aa3b3143ac","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":2218},{"digest":"sha256:4dd7b7c5bfc1ca08ddd4b0707278afc4859ff879438c4835b3cec7eb5e85a9ee","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":2218},{"digest":"sha256:80f1f8bcde1cf3b5b9a6b1ade3c90233f2738f5c0685685bdcccde311530caa8","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":2218},{"digest":"sha256:f501c3f975948f1ee60a5261efbb156abbcdd01c193bae1bbcffa6a2f2d8cb5d","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":2218},{"digest":"sha256:4f5c4c677c87e98f00b8affef87651f65c258c9b4b53ba4b237ac7f7668cac4e","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":2218},{"digest":"sha256:f3fb8be68a0eb71df0c54c0b8cb7aa192934ac7becb4cf2ac4142c925c3cbfdd","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":2218},{"digest":"sha256:969d7a3a04292e2f54c79f24f56ad520e4b355eaa2066420b63928337c22109d","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":2218},{"digest":"sha256:0e9e7fb64430afaa195198b26548c82d6e4e8a0fddd726f0f8213abf99f8528e","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"windows","os.version":"10.0.20348.707"},"size":3189},{"digest":"sha256:28a844614587f4594626999fe4193dcfc68a9f37fbc688f9af704016f3d53fa1","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"windows","os.version":"10.0.17763.2928"},"size":3189}],"mediaType":"application\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}',
}

# docker.io/library/python@sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073
PYTHON_ec43d7 = {
    "content-type": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    "digest": "sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073",
    # NOTE: the number of spaces in the manifest matters - do not change it or
    # the digests will not match!
    "manifest": """{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 8526,
      "digest": "sha256:8dec8e39f2eca1ee1f1b668619023da929039a39983de4433d42d25a7b79267c"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 54945622,
         "digest": "sha256:67e8aa6c8bbc76b1f2bccb3864b0887671833b8667dc1f6c965fcb0eac7e6402"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 5155721,
         "digest": "sha256:627e6c1e105548ea4a08354eea581f137cf368d91aeb0ad47dcb706fca54fd8b"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 10875052,
         "digest": "sha256:0670968926f6461e3135c82ba2c0ad3ebdedc0d0f41b18bda4a1e41104b8be8a"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 54578468,
         "digest": "sha256:5a8b0e20be4b4a332bc3d90b9903a5f3c0664b440fd9f1d2a1db0d4b7e6e826b"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 196562669,
         "digest": "sha256:b0b10a3a2784b06bfe0af1493ea2a0fa957ae5e0dc30fcfd1166d2558ba74e4d"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 6290722,
         "digest": "sha256:e16cd24209e80fb99ff55cf53a1c2e4a062cffad4b24c6564ef6bb4fc9428827"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 19711940,
         "digest": "sha256:c8428195afac586c96628ecdca0c2c0d2c6d5c61fcb83a32988b599a592a4dc8"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 233,
         "digest": "sha256:45ae7839fda540e13bdf4d8b465e357a5dd314d3761f53418e11ffbba330a552"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 2872318,
         "digest": "sha256:5ae8ff85c3811486f60d2f3a5c062f48674b45590a51b82ea6edcb37f2eae996"
      }
   ]
}""",
}
