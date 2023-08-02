import logging
import sys
import argparse
from data.database import (
    ImageStoragePlacement,
    ImageStorageLocation,
)
from app import features

# This is a util function used to clean up a removed location from the database
# This must be ran AFTER the location is removed from the config.yaml file, so that
# images are not still being added in the background to the location


def query_yes_no(question):
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    prompt = " [y/n] "
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " + "(or 'y' or 'n').\n")


def remove_location():
    # Get the location name from the command line
    parser = argparse.ArgumentParser(
        description="This util is used to remove a storage location from the database. This must be ran AFTER the location is removed from the config.yaml file, so that images are not still being added in the background to the location."
    )
    parser.add_argument("location", help="Name of the location")
    args = parser.parse_args()
    location_name = args.location

    if not query_yes_no(
        f"WARNING: This is a destructive operation. Are you sure you want to remove {location_name} from your storage locations?"
    ):
        print("Canceling operation...")
        return

    try:
        # Get all image placements for the location
        query = (
            ImageStoragePlacement.select()
            .join(ImageStorageLocation)
            .where(ImageStorageLocation.name == location_name)
        )

        # Delete all image placements for the location
        for image_placement in query:
            image_placement.delete().where(ImageStoragePlacement.id == image_placement.id).execute()
            print(f"Deleted placement {image_placement.id}")

        # Delete storage location from database
        ImageStorageLocation.delete().where(ImageStorageLocation.name == location_name).execute()
        print(f"Deleted location {location_name}")
    except Exception as e:
        print(f"Error removing storage location: {e}")
        return


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not features.STORAGE_REPLICATION:
        print("Storage replication is not enabled")
    else:
        remove_location()
