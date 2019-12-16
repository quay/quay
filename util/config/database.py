from data import model
from data.appr_model import blob
from data.appr_model.models import NEW_MODELS


def sync_database_with_config(config):
    """
    This ensures all implicitly required reference table entries exist in the database.
    """

    location_names = list(config.get("DISTRIBUTED_STORAGE_CONFIG", {}).keys())
    if location_names:
        model.image.ensure_image_locations(*location_names)
        blob.ensure_blob_locations(NEW_MODELS, *location_names)
