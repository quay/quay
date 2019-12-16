from data.database import Image, ImageStorage
from peewee import JOIN, fn
from app import app

orphaned = (
    ImageStorage.select()
    .where(ImageStorage.uploading == False)
    .join(Image, JOIN.LEFT_OUTER)
    .group_by(ImageStorage)
    .having(fn.Count(Image.id) == 0)
)

counter = 0
for orphan in orphaned:
    counter += 1
    print(orphan.uuid)
