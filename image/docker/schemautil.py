import json

from image.docker.interfaces import ContentRetriever


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
