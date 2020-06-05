import os
import tarfile

import marisa_trie

from util.registry.aufs import is_aufs_metadata, get_deleted_prefix
from util.registry.tarlayerformat import TarLayerFormat


class StreamLayerMerger(TarLayerFormat):
    """
    Class which creates a generator of the combined TAR data for a set of Docker layers.
    """

    def __init__(self, get_tar_stream_iterator, path_prefix=None, reporter=None):
        super(StreamLayerMerger, self).__init__(
            get_tar_stream_iterator, path_prefix, reporter=reporter
        )

        self.path_trie = marisa_trie.Trie()
        self.path_encountered = set()

        self.deleted_prefix_trie = marisa_trie.Trie()
        self.deleted_prefixes_encountered = set()

    def after_tar_layer(self):
        # Update the tries.
        self.path_trie = marisa_trie.Trie(self.path_encountered)
        self.deleted_prefix_trie = marisa_trie.Trie(self.deleted_prefixes_encountered)

    @staticmethod
    def _normalize_path(path):
        return os.path.relpath(path, "./")

    def _check_deleted(self, absolute):
        ubsolute = str(absolute)
        for prefix in self.deleted_prefix_trie.iter_prefixes(ubsolute):
            if not os.path.relpath(ubsolute, prefix).startswith(".."):
                return True

        return False

    def is_skipped_file(self, filename):
        absolute = StreamLayerMerger._normalize_path(filename)

        # Skip metadata.
        if is_aufs_metadata(absolute):
            return True

        # Check if the file is under a deleted path.
        if self._check_deleted(absolute):
            return True

        # Check if this file has already been encountered somewhere. If so,
        # skip it.
        ubsolute = str(absolute)
        if ubsolute in self.path_trie:
            return True

        return False

    def should_append_file(self, filename):
        if self.is_skipped_file(filename):
            return False

        absolute = StreamLayerMerger._normalize_path(filename)

        # Add any prefix of deleted paths to the prefix list.
        deleted_prefix = get_deleted_prefix(absolute)
        if deleted_prefix is not None:
            self.deleted_prefixes_encountered.add(deleted_prefix)
            return False

        # Otherwise, add the path to the encountered list and return it.
        self.path_encountered.add(absolute)
        return True
