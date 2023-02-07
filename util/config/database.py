from data import model


def sync_database_with_config(config):
    """
    This ensures all implicitly required reference table entries exist in the database.
    """

    location_names = list(config.get("DISTRIBUTED_STORAGE_CONFIG", {}).keys())
    if location_names:
        model.image.ensure_image_locations(*location_names)
