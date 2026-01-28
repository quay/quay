"""
Registry capabilities API endpoint.
"""

import features
from app import app
from data.model.repo_mirror import VALID_ARCHITECTURES
from endpoints.api import ApiResource, define_json_response, nickname, resource
from endpoints.decorators import anon_allowed


@resource("/v1/registry/capabilities")
class RegistryCapabilities(ApiResource):
    """
    Resource for querying registry capabilities.
    """

    schemas = {
        "RegistryCapabilitiesResponse": {
            "type": "object",
            "description": "Registry capabilities information",
            "properties": {
                "sparse_manifests": {
                    "type": "object",
                    "properties": {
                        "supported": {"type": "boolean"},
                        "required_architectures": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "optional_architectures_allowed": {"type": "boolean"},
                    },
                },
                "mirror_architectures": {
                    "type": "array",
                    "description": "Available architectures for repository mirroring filter",
                    "items": {"type": "string"},
                },
            },
        },
    }

    @nickname("getRegistryCapabilities")
    @define_json_response("RegistryCapabilitiesResponse")
    @anon_allowed
    def get(self):
        """
        Get registry capabilities.

        Returns information about supported registry features including
        sparse manifest support and required architectures.
        """
        sparse_enabled = bool(features.SPARSE_INDEX) if hasattr(features, "SPARSE_INDEX") else False
        required_archs = app.config.get("SPARSE_INDEX_REQUIRED_ARCHS", [])

        return {
            "sparse_manifests": {
                "supported": sparse_enabled,
                "required_architectures": required_archs if sparse_enabled else [],
                "optional_architectures_allowed": sparse_enabled and len(required_archs) > 0,
            },
            "mirror_architectures": sorted(VALID_ARCHITECTURES),
        }
