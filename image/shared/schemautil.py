import json

from image.shared import ManifestException
from image.shared.interfaces import ContentRetriever
from util.bytes import Bytes


class ContentRetrieverForTesting(ContentRetriever):
    def __init__(self, digests=None):
        self.digests = digests or {}

    def add_digest(self, digest, content):
        self.digests[digest] = content

    def get_manifest_bytes_with_digest(self, digest):
        return self.digests.get(digest)

    def get_blob_bytes_with_digest(self, digest):
        return self.digests.get(digest)

    @classmethod
    def for_config(cls, config_obj, digest, size, ensure_ascii=True):
        config_str = json.dumps(config_obj, ensure_ascii=ensure_ascii)
        padded_string = config_str + " " * (size - len(config_str))
        digests = {}
        digests[digest] = padded_string
        return ContentRetrieverForTesting(digests)


class _CustomEncoder(json.JSONEncoder):
    def encode(self, o):
        encoded = super(_CustomEncoder, self).encode(o)
        if isinstance(o, str):
            encoded = encoded.replace("<", "\\u003c")
            encoded = encoded.replace(">", "\\u003e")
            encoded = encoded.replace("&", "\\u0026")
        return encoded


def to_canonical_json(value, ensure_ascii=True, indent=None):
    """
    Returns the canonical JSON string form of the given value, as per the guidelines in
    https://github.com/docker/distribution/blob/master/docs/spec/json.md.

    `indent` is allowed only for the purposes of indenting for debugging.
    """
    return json.dumps(
        value,
        ensure_ascii=ensure_ascii,
        sort_keys=True,
        separators=(",", ":"),
        cls=_CustomEncoder,
        indent=indent,
    )


class LazyManifestLoader(object):
    """ Lazy loader for manifests referenced by another manifest list or index. """

    def __init__(
        self,
        manifest_data,
        content_retriever,
        supported_types,
        digest_key,
        size_key,
        media_type_key,
    ):
        self._manifest_data = manifest_data
        self._content_retriever = content_retriever
        self._loaded_manifest = None
        self._digest_key = digest_key
        self._size_key = size_key
        self._media_type_key = media_type_key
        self._supported_types = supported_types

    @property
    def manifest_obj(self):
        if self._loaded_manifest is not None:
            return self._loaded_manifest

        self._loaded_manifest = self._load_manifest()
        return self._loaded_manifest

    def _load_manifest(self):
        digest = self._manifest_data[self._digest_key]
        size = self._manifest_data[self._size_key]
        manifest_bytes = self._content_retriever.get_manifest_bytes_with_digest(digest)
        if manifest_bytes is None:
            raise ManifestException("Could not find child manifest with digest `%s`" % digest)

        if len(manifest_bytes) != size:
            raise ManifestException(
                "Size of manifest does not match that retrieved: %s vs %s",
                len(manifest_bytes),
                size,
            )

        content_type = self._manifest_data[self._media_type_key]
        if content_type not in self._supported_types:
            raise ManifestException(
                "Unknown or unsupported manifest media type `%s` not found in %s"
                % (content_type, self._supported_types.keys())
            )

        return self._supported_types[content_type](
            Bytes.for_string_or_unicode(manifest_bytes), validate=False
        )
