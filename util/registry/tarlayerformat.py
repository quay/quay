import os
import tarfile
import copy

from abc import ABCMeta, abstractmethod
from collections import defaultdict
from six import add_metaclass

from util.abchelpers import nooper


class TarLayerReadException(Exception):
    """
    Exception raised when reading a layer has failed.
    """

    pass


# 9MB (+ padding below) so that it matches the 10MB expected by Gzip.
CHUNK_SIZE = 1024 * 1024 * 9


@add_metaclass(ABCMeta)
class TarLayerFormatterReporter(object):
    @abstractmethod
    def report_pass(self, stream_count):
        """
        Reports a formatting pass.
        """
        pass


@nooper
class NoopReporter(TarLayerFormatterReporter):
    pass


@add_metaclass(ABCMeta)
class TarLayerFormat(object):
    """
    Class which creates a generator of the combined TAR data.
    """

    def __init__(self, tar_stream_getter_iterator, path_prefix=None, reporter=None):
        self.tar_stream_getter_iterator = tar_stream_getter_iterator
        self.path_prefix = path_prefix or ""
        self.reporter = reporter or NoopReporter()

    def get_generator(self):
        for stream_getter in self.tar_stream_getter_iterator():
            current_tar_stream = stream_getter()

            # Read the current TAR. If it is empty, we just continue
            # to the next one.
            tar_file = TarLayerFormat._tar_file_from_stream(current_tar_stream)
            if not tar_file:
                continue

            # For each of the tar entries, yield them IF and ONLY IF we have not
            # encountered the path before.
            dangling_hard_links = defaultdict(list)
            try:
                for tar_info in tar_file:
                    if not self.should_append_file(tar_info.name):
                        continue

                    # Note: We use a copy here because we need to make sure we copy over all the internal
                    # data of the tar header. We cannot use frombuf(tobuf()), however, because it doesn't
                    # properly handle large filenames.
                    clone = copy.deepcopy(tar_info)
                    clone.name = os.path.join(self.path_prefix, clone.name)

                    # If the entry is a *hard* link, then prefix it as well. Soft links are relative.
                    if clone.linkname and clone.type == tarfile.LNKTYPE:
                        # If the entry is a dangling hard link, we skip here. Dangling hard links will be handled
                        # in a second pass.
                        if self.is_skipped_file(tar_info.linkname):
                            dangling_hard_links[tar_info.linkname].append(tar_info)
                            continue

                        clone.linkname = os.path.join(self.path_prefix, clone.linkname)

                    # Yield the tar header.
                    yield clone.tobuf()

                    # Try to extract any file contents for the tar. If found, we yield them as well.
                    if tar_info.isreg():
                        for block in TarLayerFormat._emit_file(tar_file, tar_info):
                            yield block
            except UnicodeDecodeError as ude:
                raise TarLayerReadException("Decode error: %s" % ude)

            # Close the layer stream now that we're done with it.
            tar_file.close()

            # If there are any dangling hard links, open a new stream and retarget the dangling hard
            # links to a new copy of the contents, which will be placed under the *first* dangling hard
            # link's name.
            if len(dangling_hard_links) > 0:
                tar_file = TarLayerFormat._tar_file_from_stream(stream_getter())
                if not tar_file:
                    raise TarLayerReadException("Could not re-read tar layer")

                for tar_info in tar_file:
                    # If we encounter a file that holds the data for a dangling link,
                    # emit it under the name of the first dangling hard link. All other
                    # dangling hard links will be retargeted to this first name.
                    if tar_info.name in dangling_hard_links:
                        first_dangling = dangling_hard_links[tar_info.name][0]

                        # Copy the first dangling hard link, change it to a normal file,
                        # and emit the deleted file's contents for it.
                        clone = copy.deepcopy(first_dangling)
                        clone.name = os.path.join(self.path_prefix, first_dangling.name)
                        clone.type = tar_info.type
                        clone.size = tar_info.size
                        clone.pax_headers = tar_info.pax_headers
                        yield clone.tobuf()

                        for block in TarLayerFormat._emit_file(tar_file, tar_info):
                            yield block

                    elif (
                        tar_info.type == tarfile.LNKTYPE
                        and tar_info.linkname in dangling_hard_links
                        and not self.is_skipped_file(tar_info.name)
                    ):
                        # Retarget if necessary. All dangling hard links (but the first) will
                        # need to be retargeted.
                        first_dangling = dangling_hard_links[tar_info.linkname][0]
                        if tar_info.name == first_dangling.name:
                            # Skip; the first dangling is handled above.
                            continue

                        # Retarget the hard link to the first dangling hard link.
                        clone = copy.deepcopy(tar_info)
                        clone.name = os.path.join(self.path_prefix, clone.name)
                        clone.linkname = os.path.join(self.path_prefix, first_dangling.name)
                        yield clone.tobuf()

                # Close the layer stream now that we're done with it.
                tar_file.close()

            # Conduct any post-tar work.
            self.after_tar_layer()
            self.reporter.report_pass(2 if len(dangling_hard_links) > 0 else 1)

        # Last two records are empty in TAR spec.
        yield b"\0" * 512
        yield b"\0" * 512

    @abstractmethod
    def is_skipped_file(self, filename):
        """
        Returns true if the file with the given name will be skipped during append.
        """
        pass

    @abstractmethod
    def should_append_file(self, filename):
        """
        Returns true if the file with the given name should be appended when producing the new TAR.
        """
        pass

    @abstractmethod
    def after_tar_layer(self):
        """
        Invoked after a TAR layer is added, to do any post-add work.
        """
        pass

    @staticmethod
    def _tar_file_from_stream(stream):
        tar_file = None
        try:
            tar_file = tarfile.open(mode="r|*", fileobj=stream)
        except tarfile.ReadError as re:
            if str(re) != "empty file":
                raise TarLayerReadException("Could not read layer")

        return tar_file

    @staticmethod
    def _emit_file(tar_file, tar_info):
        file_stream = tar_file.extractfile(tar_info)
        if file_stream is not None:
            length = 0
            while True:
                current_block = file_stream.read(CHUNK_SIZE)
                if not len(current_block):
                    break

                yield current_block
                length += len(current_block)

            file_stream.close()

            # Files must be padding to 512 byte multiples.
            if length % 512 != 0:
                yield b"\0" * (512 - (length % 512))
