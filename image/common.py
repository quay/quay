import tarfile
from util.registry.gzipwrap import GzipWrap


class TarImageFormatter(object):
    """
    Base class for classes which produce a tar containing image and layer data.
    """

    def build_stream(
        self,
        tag,
        manifest,
        synthetic_image_id,
        layer_iterator,
        tar_stream_getter_iterator,
        reporter=None,
    ):
        """
        Builds and streams a synthetic .tar.gz that represents the formatted tar created by this
        class's implementation.
        """
        return GzipWrap(
            self.stream_generator(
                tag,
                manifest,
                synthetic_image_id,
                layer_iterator,
                tar_stream_getter_iterator,
                reporter=reporter,
            )
        )

    def stream_generator(
        self,
        tag,
        manifest,
        synthetic_image_id,
        layer_iterator,
        tar_stream_getter_iterator,
        reporter=None,
    ):
        raise NotImplementedError

    def tar_file(self, name, contents, mtime=None):
        """
        Returns the tar binary representation for a file with the given name and file contents.
        """
        assert isinstance(contents, bytes)
        length = len(contents)
        tar_data = self.tar_file_header(name, length, mtime=mtime)
        tar_data += contents
        tar_data += self.tar_file_padding(length)
        return tar_data

    def tar_file_padding(self, length):
        """
        Returns tar file padding for file data of the given length.
        """
        if length % 512 != 0:
            return b"\0" * (512 - (length % 512))

        return b""

    def tar_file_header(self, name, file_size, mtime=None):
        """
        Returns tar file header data for a file with the given name and size.
        """
        info = tarfile.TarInfo(name=name)
        info.type = tarfile.REGTYPE
        info.size = file_size

        if mtime is not None:
            info.mtime = mtime
        return info.tobuf()

    def tar_folder(self, name, mtime=None):
        """
        Returns tar file header data for a folder with the given name.
        """
        info = tarfile.TarInfo(name=name)
        info.type = tarfile.DIRTYPE

        if mtime is not None:
            info.mtime = mtime

        # allow the directory to be readable by non-root users
        info.mode = 0o755
        return info.tobuf()
