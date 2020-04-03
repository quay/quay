from data.database import Manifest, ManifestLegacyImage, Image


def get_legacy_image_for_manifest(manifest_id):
    """
    Returns the legacy image associated with the given manifest, if any, or None if none.
    """
    try:
        query = (
            ManifestLegacyImage.select(ManifestLegacyImage, Image)
            .join(Image)
            .where(ManifestLegacyImage.manifest == manifest_id)
        )
        return query.get().image
    except ManifestLegacyImage.DoesNotExist:
        return None
