OCI_IMAGE_MANIFEST_CONTENT_TYPE = "application/vnd.oci.image.manifest.v1+json"
OCI_IMAGE_INDEX_CONTENT_TYPE = "application/vnd.oci.image.index.v1+json"
OCI_IMAGE_CONFIG_CONTENT_TYPE = "application/vnd.oci.image.config.v1+json"

OCI_IMAGE_TAR_LAYER_CONTENT_TYPE = "application/vnd.oci.image.layer.v1.tar"
OCI_IMAGE_TAR_GZIP_LAYER_CONTENT_TYPE = "application/vnd.oci.image.layer.v1.tar+gzip"

OCI_IMAGE_DISTRIBUTABLE_LAYER_CONTENT_TYPES = [
    OCI_IMAGE_TAR_LAYER_CONTENT_TYPE,
    OCI_IMAGE_TAR_GZIP_LAYER_CONTENT_TYPE,
]

OCI_IMAGE_TAR_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPE = (
    "application/vnd.oci.image.layer.nondistributable.v1.tar"
)
OCI_IMAGE_TAR_GZIP_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPE = (
    "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip"
)

OCI_IMAGE_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPES = [
    OCI_IMAGE_TAR_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPE,
    OCI_IMAGE_TAR_GZIP_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPE,
]

OCI_IMAGE_LAYER_CONTENT_TYPES = (
    OCI_IMAGE_DISTRIBUTABLE_LAYER_CONTENT_TYPES + OCI_IMAGE_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPES
)

OCI_CONTENT_TYPES = {OCI_IMAGE_MANIFEST_CONTENT_TYPE, OCI_IMAGE_INDEX_CONTENT_TYPE}

ALLOWED_ARTIFACT_TYPES = [OCI_IMAGE_CONFIG_CONTENT_TYPE]
ADDITIONAL_LAYER_CONTENT_TYPES = []


def register_artifact_type(artifact_config_type, artifact_layer_types):
    if artifact_config_type not in ALLOWED_ARTIFACT_TYPES:
        ALLOWED_ARTIFACT_TYPES.append(artifact_config_type)

    for layer_type in artifact_layer_types:
        if layer_type not in ADDITIONAL_LAYER_CONTENT_TYPES:
            ADDITIONAL_LAYER_CONTENT_TYPES.append(layer_type)
