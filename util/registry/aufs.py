import os

AUFS_METADATA = ".wh..wh."
AUFS_WHITEOUT = ".wh."
AUFS_WHITEOUT_PREFIX_LENGTH = len(AUFS_WHITEOUT)


def is_aufs_metadata(absolute):
    """
    Returns whether the given absolute references an AUFS metadata file.
    """
    filename = os.path.basename(absolute)
    return filename.startswith(AUFS_METADATA) or absolute.startswith(AUFS_METADATA)


def get_deleted_filename(absolute):
    """
    Returns the name of the deleted file referenced by the AUFS whiteout file at the given path or
    None if the file path does not reference a whiteout file.
    """
    filename = os.path.basename(absolute)
    if not filename.startswith(AUFS_WHITEOUT):
        return None

    return filename[AUFS_WHITEOUT_PREFIX_LENGTH:]


def get_deleted_prefix(absolute):
    """
    Returns the path prefix of the deleted file referenced by the AUFS whiteout file at the given
    path or None if the file path does not reference a whiteout file.
    """
    deleted_filename = get_deleted_filename(absolute)
    if deleted_filename is None:
        return None

    dirname = os.path.dirname(absolute)
    return os.path.join("/", dirname, deleted_filename)[1:]
