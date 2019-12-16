from data.database import Image, ImageStorage

query = ImageStorage.select().annotate(Image)

saved_bytes = 0
total_bytes = 0

for storage in query:
    if storage.image_size is not None:
        saved_bytes += (storage.count - 1) * storage.image_size
        total_bytes += storage.count * storage.image_size

print("Saved: %s" % saved_bytes)
print("Total: %s" % total_bytes)
