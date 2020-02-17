from collections import namedtuple

ManifestImageLayer = namedtuple(
    "ManifestImageLayer",
    [
        "layer_id",
        "compressed_size",
        "is_remote",
        "urls",
        "command",
        "blob_digest",
        "created_datetime",
        "author",
        "comment",
        "internal_layer",
    ],
)
