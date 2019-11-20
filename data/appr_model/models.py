from collections import namedtuple

from data.database import (
    ApprTag,
    ApprTagKind,
    ApprBlobPlacementLocation,
    ApprManifestList,
    ApprManifestBlob,
    ApprBlob,
    ApprManifestListManifest,
    ApprManifest,
    ApprBlobPlacement,
    ApprChannel,
)

ModelsRef = namedtuple(
    "ModelsRef",
    [
        "Tag",
        "TagKind",
        "BlobPlacementLocation",
        "ManifestList",
        "ManifestBlob",
        "Blob",
        "ManifestListManifest",
        "Manifest",
        "BlobPlacement",
        "Channel",
        "manifestlistmanifest_set_name",
        "tag_set_prefetch_name",
    ],
)

NEW_MODELS = ModelsRef(
    ApprTag,
    ApprTagKind,
    ApprBlobPlacementLocation,
    ApprManifestList,
    ApprManifestBlob,
    ApprBlob,
    ApprManifestListManifest,
    ApprManifest,
    ApprBlobPlacement,
    ApprChannel,
    "apprmanifestlistmanifest_set",
    "apprtag_set",
)
