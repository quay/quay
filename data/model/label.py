from cachetools.func import lru_cache

from data.database import (
    MediaType,
    LabelSourceType,
)


@lru_cache(maxsize=1)
def get_label_source_types():
    source_type_map = {}
    for kind in LabelSourceType.select():
        source_type_map[kind.id] = kind.name
        source_type_map[kind.name] = kind.id

    return source_type_map


@lru_cache(maxsize=1)
def get_media_types():
    media_type_map = {}
    for kind in MediaType.select():
        media_type_map[kind.id] = kind.name
        media_type_map[kind.name] = kind.id

    return media_type_map
