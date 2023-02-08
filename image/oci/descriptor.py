DESCRIPTOR_MEDIATYPE_KEY = "mediaType"
DESCRIPTOR_SIZE_KEY = "size"
DESCRIPTOR_DIGEST_KEY = "digest"
DESCRIPTOR_URLS_KEY = "urls"
DESCRIPTOR_ANNOTATIONS_KEY = "annotations"
DESCRIPTOR_DATA_KEY = "data"
DESCRIPTOR_ARTIFACT_TYPE_KEY = "artifactType"


def get_descriptor_schema(
    allowed_media_types=None, additional_properties=None, additional_required=None
):
    properties = {
        DESCRIPTOR_MEDIATYPE_KEY: {
            "type": "string",
            "description": "The MIME type of the referenced manifest",
        },
        DESCRIPTOR_SIZE_KEY: {
            "type": "number",
            "description": "The size in bytes of the object. This field exists so that a "
            + "client will have an expected size for the content before "
            + "validating. If the length of the retrieved content does not "
            + "match the specified length, the content should not be trusted.",
        },
        DESCRIPTOR_DIGEST_KEY: {
            "type": "string",
            "description": "The content addressable digest of the manifest in the blob store",
        },
        DESCRIPTOR_ANNOTATIONS_KEY: {
            "type": "object",
            "description": "The annotations, if any, on this descriptor",
            "additionalProperties": True,
        },
        DESCRIPTOR_URLS_KEY: {
            "type": "array",
            "description": "This OPTIONAL property specifies a list of URIs from which this object MAY be downloaded. Each entry MUST conform to RFC 3986. Entries SHOULD use the http and https schemes, as defined in RFC 7230.",
            "items": {
                "type": "string",
            },
        },
        DESCRIPTOR_DATA_KEY: {
            "type": ["string", "null"],
            "description": "This OPTIONAL property contains an embedded representation of the referenced content. Values MUST conform to the Base 64 encoding, as defined in RFC 4648.",
        },
        DESCRIPTOR_ARTIFACT_TYPE_KEY: {
            "type": ["string", "null"],
            "description": "This OPTIONAL property contains the type of an artifact when the descriptor points to an artifact. This is the value of artifactType when the descriptor references an artifact manifest. This is the value of the config descriptor mediaType when the descriptor references an image manifest.",
        },
    }

    if allowed_media_types is not None:
        properties[DESCRIPTOR_MEDIATYPE_KEY]["enum"] = allowed_media_types

    if additional_properties:
        properties.update(additional_properties)

    return {
        "type": "object",
        "properties": properties,
        "required": [
            DESCRIPTOR_MEDIATYPE_KEY,
            DESCRIPTOR_SIZE_KEY,
            DESCRIPTOR_DIGEST_KEY,
        ]
        + (additional_required or []),
    }
