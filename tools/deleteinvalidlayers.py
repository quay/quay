from data.database import (
    ImageStorage,
    Image,
    ImageStoragePlacement,
    ImageStorageLocation,
    RepositoryTag,
)
from data import model
from app import storage as storage_system
from tqdm import tqdm


def find_broken_storages():
    broken_storages = set()

    print("Checking storages...")
    placement_count = ImageStoragePlacement.select().count()
    placements = (
        ImageStoragePlacement.select()
        .join(ImageStorage)
        .switch(ImageStoragePlacement)
        .join(ImageStorageLocation)
    )

    for placement in tqdm(placements, total=placement_count):
        path = model.storage.get_layer_path(placement.storage)
        if not storage_system.exists([placement.location.name], path):
            broken_storages.add(placement.storage.id)

    return list(broken_storages)


def delete_broken_layers():
    result = input('Please make sure your registry is not running and enter "GO" to continue: ')
    if result != "GO":
        print("Declined to run")
        return

    broken_storages = find_broken_storages()
    if not broken_storages:
        print("No broken layers found")
        return

    # Find all the images referencing the broken layers.
    print("Finding broken images...")
    IMAGE_BATCH_SIZE = 100

    all_images = []
    for i in tqdm(list(range(0, len(broken_storages) / IMAGE_BATCH_SIZE))):
        start = i * IMAGE_BATCH_SIZE
        end = (i + 1) * IMAGE_BATCH_SIZE

        images = (
            Image.select().join(ImageStorage).where(Image.storage << broken_storages[start:end])
        )
        all_images.extend(images)

    if not all_images:
        print("No broken layers found")
        return

    # Find all the tags containing the images.
    print("Finding associated tags for %s images..." % len(all_images))
    all_tags = {}
    for image in tqdm(all_images):
        query = model.tag.get_matching_tags(
            image.docker_image_id, image.storage.uuid, RepositoryTag
        )
        for tag in query:
            all_tags[tag.id] = tag

    # Ask to delete them.
    print("")
    print("The following tags were found to reference invalid images:")
    for tag in list(all_tags.values()):
        print("%s/%s: %s" % (tag.repository.namespace_user.username, tag.repository.name, tag.name))

    if not all_tags:
        print("(Tags in time machine)")

    print("")
    result = input(
        'Enter "DELETENOW" to delete these tags and ALL associated images (THIS IS PERMANENT): '
    )
    if result != "DELETENOW":
        print("Declined to delete")
        return

    print("")
    print("Marking tags to be GCed...")
    for tag in tqdm(list(all_tags.values())):
        tag.lifetime_end_ts = 0
        tag.save()

    print("GCing all repositories...")
    for tag in tqdm(list(all_tags.values())):
        model.repository.garbage_collect_repo(tag.repository)

    print("All done! You may now restart your registry.")


delete_broken_layers()
