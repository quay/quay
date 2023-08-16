from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)

# docker.io/library/nginx:1.23.1
NGINX_1_23_1 = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:790711e34858c9b0741edffef6ed3d8199d8faa33f2870dea5db70f16384df79",
    "manifest": r"""{"manifests":[{"digest":"sha256:f26fbadb0acab4a21ecb4e337a326907e61fbec36c9a9b52e725669d99ed1261","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":1570},{"digest":"sha256:df0d884bcf2e51ad370f16bcbe6d4cef68fd8057b63da89b77c228a680e7ed8a","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":1570},{"digest":"sha256:6575132f2098216b9ac0140aaa4603ef55054891d7917200f4b827e8aa557ed3","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":1570},{"digest":"sha256:f5bee9654d19467f16c259fb577c4a28c082f8008914befd30805f803fa56e99","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":1570},{"digest":"sha256:d830cc525721daa5769bf9876db421987aefeff16c5074edc0c6b9061f8ff359","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":1570},{"digest":"sha256:5c134d3a19dc5fb01f4e7df9c36e3c054153e661b4bd3472858940894569d829","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":1570},{"digest":"sha256:f1d915d7215a80b1a294ec8e9005a4b7984e650e06cb9b52f57e830576245c74","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":1570},{"digest":"sha256:ead4adf366b0333e5f7e10f32b2b7814b3ea39807db3c3ac029d4404140da5b0","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":1570}],"mediaType":"application\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}""",
}


# docker.io/library/nginx@sha256:f26fbadb0acab4a21ecb4e337a326907e61fbec36c9a9b52e725669d99ed1261
# part of docker.io/library/nginx:1.23.1
NGINX_1_23_1_LINUX_AMD64 = {
    "content-type": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    "digest": "sha256:f26fbadb0acab4a21ecb4e337a326907e61fbec36c9a9b52e725669d99ed1261",
    "manifest": r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 7653,
      "digest": "sha256:b692a91e4e1582db97076184dae0b2f4a7a86b68c4fe6f91affa50ae06369bf5"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 31366757,
         "digest": "sha256:1efc276f4ff952c055dea726cfc96ec6a4fdb8b62d9eed816bd2b788f2860ad7"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 25348083,
         "digest": "sha256:baf2da91597d101646b307b706d06b048862192b127f74b1079d374d902e32f4"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 603,
         "digest": "sha256:05396a986fd3f3739cc890e30a2ed78e377c6a2b24d9f0ebe99ff3349aedc603"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 891,
         "digest": "sha256:6a17c8e7063d97ef72e89f7d4673935ff9a2b7c179bea1726852399219118f65"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 664,
         "digest": "sha256:27e0d286aeab484653fdf0f736d5f7a2fbcc572e387ec8a1d6ccf0e74b6bfefc"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 1391,
         "digest": "sha256:b1349eea8fc5b5eebb633c2cd79fc24a915fcb00279de24684bb07e349e8eab3"
      }
   ]
}""",
}


# docker.io/library/nginx:1.22
NGINX_1_22 = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:d2a292b137508356bef03867bea9ccac4ae6bb6acd41d2ca3c859b7213109896",
    "manifest": r"""{"manifests":[{"digest":"sha256:813c400b452834cea3f6b3231168a64a4310369ba9f0c571b2bd11c437d4284a","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":1570},{"digest":"sha256:ee694b5c53c8c59a32a89ddf39309ae26970f2be327d290d7be4f45841eb7669","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":1570},{"digest":"sha256:9f2239a5e5400912dda2530bd1332750f2fadf646b7f360f6e95c4ee31ce315b","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":1570},{"digest":"sha256:4e0cfdaa91a6589dd3d32ebfdb63c2f3b9b770d82c4a2251ee07acf5b1fabccf","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":1570},{"digest":"sha256:c8936bee84a7816b693d32994bea27774b972f4e2d2e858c38035a9bc4aa5c3d","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":1570},{"digest":"sha256:a888cc4d73a317f4c8efc3ae24b1e1cb3e7f5652669c2241af1fc769a56a50a7","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":1570},{"digest":"sha256:6a2ee4fc1499a932b4eb3d8b8c820c827f9e75bd5c302757fe8394649c543457","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":1570},{"digest":"sha256:d5f436f9bd1dc2f8ded4d84e9b2556d5998a0938fc2464de59f68ad16c59b16f","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":1570}],"mediaType":"application\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}""",
}


# docker.io/library/nginx@sha256:813c400b452834cea3f6b3231168a64a4310369ba9f0c571b2bd11c437d4284a
# as part of docker.io/library/nginx:1.22
NGINX_1_22_LINUX_AMD64 = {
    "content-type": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    "digest": "sha256:813c400b452834cea3f6b3231168a64a4310369ba9f0c571b2bd11c437d4284a",
    "manifest": r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 7636,
      "digest": "sha256:7d2669aee584c0daa33efe695dd4fe78e7e1ab2d1e76fec424c9dc8a6b30b205"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 31366757,
         "digest": "sha256:1efc276f4ff952c055dea726cfc96ec6a4fdb8b62d9eed816bd2b788f2860ad7"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 25346133,
         "digest": "sha256:f083c3ec9303dc9d001e8607c7c9cd327529e45e2886a4bafe1ec8263a592981"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 601,
         "digest": "sha256:4670ba2d31b0d9c0394e3d23adc1b6e6ab6ed02af61310c0219307423d52832f"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 895,
         "digest": "sha256:883d1b430e78289aaf2e990ff6a29759355e238347e019d418eed53d1193c64f"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 667,
         "digest": "sha256:80453319cc3e3f9d1b8b24e9238bb2afa83e53a8a0d9554c2d66757edf9442d3"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 1395,
         "digest": "sha256:75efce6a46743acc3515c455273a0775c12ab5a24c5df04c0887db1f68958241"
      }
   ]
}""",
}


UBI8_LINUX_AMD64 = {
    "content-type": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    "digest": "sha256:b69959407d21e8a062e0416bf13405bb2b71ed7a84dde4158ebafacfa06f5578",
    "manifest": r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 1456,
      "digest": "sha256:ec3f0931a6e6b6855d76b2d7b0be30e81860baccd891b2e243280bf1cd8ad710"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 772795,
         "digest": "sha256:009932687766e1520a47aa9de3bfe97ffdb1b6cad0b08d5078bad60329f13f19"
      }
   ]
}""",
}


UBI8_LATEST = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:bd5b5d4f108773d02b2f3aa930feaa08067091e96ecf45f10e98e76383ff7af9",
    "manifest": r"""{
  "manifests": [
    {
      "digest": "sha256:b69959407d21e8a062e0416bf13405bb2b71ed7a84dde4158ebafacfa06f5578",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:ce06da2e3e24e4ac99f6da067bcab57e3dcc2ea4582da16e5d97003c32a6fa8c",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm",
        "os": "linux",
        "variant": "v5"
      },
      "size": 527
    },
    {
      "digest": "sha256:4bcaeca137ff437584eb96c41b425b4010167a0156f0a9f7bbc26f9a36d536df",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm",
        "os": "linux",
        "variant": "v6"
      },
      "size": 527
    },
    {
      "digest": "sha256:5ca5e3117f6f9bdb803ea67af89203b7e62a28c7456c098809f712a7294ceaaa",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm",
        "os": "linux",
        "variant": "v7"
      },
      "size": 527
    },
    {
      "digest": "sha256:2a64d8b2861154867e526a189eddfc7afaf12c13c9b67a56b7adcd56895818ae",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm64",
        "os": "linux",
        "variant": "v8"
      },
      "size": 527
    },
    {
      "digest": "sha256:2d06e13d26ccd313d3029e44f48d69ad4c98d0bf934692befb288dc6404a3ad9",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "386",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:5ff091cdd7eadbe140ac122d166a8f20f346a72d7eea9ababbd0546e0ca73049",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "mips64le",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:3f6c90002d9d31b871ee132953db48422b3dea4815d662d9e54ca389d2366800",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "ppc64le",
        "os": "linux"
      },
      "size": 528
    },
    {
      "digest": "sha256:bb2a26ee650f0f3f49a2676bc50bcc4f44d9f1f6c7c12b7b4acc17beda338af4",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "riscv64",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:02cdeb6ebe57001c73da6adf199eb94a94b6d8c5ef7a92432928d1b3861ff53c",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "s390x",
        "os": "linux"
      },
      "size": 528
    }
  ],
  "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
  "schemaVersion": 2
}""",
}


# docker.io/library/python:bullseye
PYTHON_BULLSEYE = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:90213d7c778e0c59de4420925fc35ff76d8d91f6b0ddcf16789af05b78ddc779",
    "manifest": '{"manifests":[{"digest":"sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":2218},{"digest":"sha256:7f2fa3897549ad7a3b64353c5f7bf61021d22ec4073137804660d1aa3b3143ac","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":2218},{"digest":"sha256:4dd7b7c5bfc1ca08ddd4b0707278afc4859ff879438c4835b3cec7eb5e85a9ee","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":2218},{"digest":"sha256:80f1f8bcde1cf3b5b9a6b1ade3c90233f2738f5c0685685bdcccde311530caa8","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":2218},{"digest":"sha256:f501c3f975948f1ee60a5261efbb156abbcdd01c193bae1bbcffa6a2f2d8cb5d","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":2218},{"digest":"sha256:4f5c4c677c87e98f00b8affef87651f65c258c9b4b53ba4b237ac7f7668cac4e","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":2218},{"digest":"sha256:f3fb8be68a0eb71df0c54c0b8cb7aa192934ac7becb4cf2ac4142c925c3cbfdd","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":2218},{"digest":"sha256:969d7a3a04292e2f54c79f24f56ad520e4b355eaa2066420b63928337c22109d","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":2218}],"mediaType":"application\\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}',
}

# docker.io/library/python:latest
PYTHON_LATEST = {
    "content-type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    "digest": "sha256:567018293e51a89db96ce4c9679fdefc89b3d17a9fe9e94c0091b04ac5bb4e89",
    "manifest": '{"manifests":[{"digest":"sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":2218},{"digest":"sha256:7f2fa3897549ad7a3b64353c5f7bf61021d22ec4073137804660d1aa3b3143ac","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":2218},{"digest":"sha256:4dd7b7c5bfc1ca08ddd4b0707278afc4859ff879438c4835b3cec7eb5e85a9ee","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":2218},{"digest":"sha256:80f1f8bcde1cf3b5b9a6b1ade3c90233f2738f5c0685685bdcccde311530caa8","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":2218},{"digest":"sha256:f501c3f975948f1ee60a5261efbb156abbcdd01c193bae1bbcffa6a2f2d8cb5d","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":2218},{"digest":"sha256:4f5c4c677c87e98f00b8affef87651f65c258c9b4b53ba4b237ac7f7668cac4e","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":2218},{"digest":"sha256:f3fb8be68a0eb71df0c54c0b8cb7aa192934ac7becb4cf2ac4142c925c3cbfdd","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":2218},{"digest":"sha256:969d7a3a04292e2f54c79f24f56ad520e4b355eaa2066420b63928337c22109d","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":2218},{"digest":"sha256:0e9e7fb64430afaa195198b26548c82d6e4e8a0fddd726f0f8213abf99f8528e","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"windows","os.version":"10.0.20348.707"},"size":3189},{"digest":"sha256:28a844614587f4594626999fe4193dcfc68a9f37fbc688f9af704016f3d53fa1","mediaType":"application\\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"windows","os.version":"10.0.17763.2928"},"size":3189}],"mediaType":"application\\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}',
}

# docker.io/library/python@sha256:ec43d739179d1979274d05ac081e279c97cfe5ca31777b7de3ec77ff82909073
PYTHON_LINUX_AMD64 = {
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
