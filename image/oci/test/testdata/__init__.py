# quay.io/openshift-scale/etcd-perf@sha256:6416299892584b515393076863b75f192ca6cf98583d83b8e583ec3b6f2a8a5e
OCI_IMAGE_INDEX_MANIFEST = '{"schemaVersion":2,"manifests":[{"mediaType":"application/vnd.oci.image.manifest.v1+json","digest":"sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3","size":1334,"platform":{"architecture":"amd64","os":"linux"}},{"mediaType":"application/vnd.oci.image.manifest.v1+json","digest":"sha256:4eca3b97fcd88a47c6454d0cb9ff59aeb4baeca332387e87421b2302bfc724e6","size":1334,"platform":{"architecture":"arm64","os":"linux"}},{"mediaType":"application/vnd.oci.image.manifest.v1+json","digest":"sha256:dacec655f2712b6f5eabc007b154959bba7add6aafdcab883e314f16e491f9d3","size":1334,"platform":{"architecture":"ppc64le","os":"linux"}}]}'  # noqa E501

OCI_IMAGE_INDEX_MANIFEST_WITHOUT_AMD = """{
  "schemaVersion": 2,
  "manifests": [
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "size": 7143,
      "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
      "platform": {
        "architecture": "ppc64le",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "size": 7682,
      "digest": "sha256:5b0bcabd1ed22e9fb1310cf6c2dec7cdef19f0ad69efa1f392e94a4333501270",
      "platform": {
        "architecture": "intel386",
        "os": "linux"
      }
    }
  ],
  "annotations": {
    "com.example.key1": "value1",
    "com.example.key2": "value2"
  }
}"""
