WHENCE_ABSOLUTE = 0
WHENCE_RELATIVE = 1
WHENCE_RELATIVE_END = 2

READ_UNTIL_END = -1


class BaseStreamFilelike(object):
    def __init__(self, fileobj):
        self._fileobj = fileobj
        self._cursor_position = 0

    def close(self):
        self._fileobj.close()

    def read(self, size=READ_UNTIL_END):
        buf = self._fileobj.read(size)
        if buf is None:
            return None
        self._cursor_position += len(buf)
        return buf

    def tell(self):
        return self._cursor_position

    def seek(self, index, whence=WHENCE_ABSOLUTE):
        num_bytes_to_ff = 0
        if whence == WHENCE_ABSOLUTE:
            if index < self._cursor_position:
                raise IOError("Cannot seek backwards")
            num_bytes_to_ff = index - self._cursor_position

        elif whence == WHENCE_RELATIVE:
            if index < 0:
                raise IOError("Cannnot seek backwards")
            num_bytes_to_ff = index

        elif whence == WHENCE_RELATIVE_END:
            raise IOError("Stream does not have a known end point")

        bytes_forward = num_bytes_to_ff
        while num_bytes_to_ff > 0:
            buf = self._fileobj.read(num_bytes_to_ff)
            if not buf:
                raise IOError("Seek past end of file")
            num_bytes_to_ff -= len(buf)

        self._cursor_position += bytes_forward
        return bytes_forward

    def readable(self):
        # Depending on the "transfer-encoding" header, the returned stream will either be a
        # Flask stream, or a gunicorn wrapped stream (see endpoints/v2/__init__.py):
        # - https://github.com/pallets/werkzeug/blob/master/src/werkzeug/wsgi.py#L205
        # - https://github.com/benoitc/gunicorn/blob/master/gunicorn/http/body.py#L177
        #
        # In the latter case, gunicorn's wrapper class does not implement the full object-file
        # api expected (e.g `readable` is missing).
        if hasattr(self._fileobj, "readable"):
            return self._fileobj.readable()
        try:
            self.read(0)
            return True
        except ValueError:
            return False


class SocketReader(BaseStreamFilelike):
    def __init__(self, fileobj):
        super(SocketReader, self).__init__(fileobj)
        self.handlers = []

    def add_handler(self, handler):
        self.handlers.append(handler)

    def read(self, size=READ_UNTIL_END):
        buf = super(SocketReader, self).read(size)
        for handler in self.handlers:
            handler(buf)
        return buf


def wrap_with_handler(in_fp, handler):
    wrapper = SocketReader(in_fp)
    wrapper.add_handler(handler)
    return wrapper


class FilelikeStreamConcat(object):
    """
    A buffered (binary) file-like object which concats all the file-like objects in the specified generator into a
    single stream.
    """

    def __init__(self, file_generator):
        self._file_generator = file_generator
        self._current_file = next(file_generator)
        self._current_position = 0
        self._closed = False

    def tell(self):
        return self._current_position

    def close(self):
        self._closed = True

    def read(self, size=READ_UNTIL_END):
        buf = b""
        current_size = size

        while size == READ_UNTIL_END or len(buf) < size:
            current_buf = self._current_file.read(current_size)
            if current_buf:
                buf += current_buf
                self._current_position += len(current_buf)
                if size != READ_UNTIL_END:
                    current_size -= len(current_buf)

            else:
                # That file was out of data, prime a new one
                self._current_file.close()
                try:
                    self._current_file = next(self._file_generator)
                except StopIteration:
                    return buf

        return buf


class StreamSlice(BaseStreamFilelike):
    """
    A file-like object which returns a file-like object that represents a slice of the data in the
    specified file obj.

    All methods will act as if the slice is its own file.
    """

    def __init__(self, fileobj, start_offset=0, end_offset_exclusive=READ_UNTIL_END):
        super(StreamSlice, self).__init__(fileobj)
        self._end_offset_exclusive = end_offset_exclusive
        self._start_offset = start_offset

        if start_offset > 0:
            self.seek(start_offset)

    def read(self, size=READ_UNTIL_END):
        if self._end_offset_exclusive == READ_UNTIL_END:
            # We weren't asked to limit the end of the stream
            return super(StreamSlice, self).read(size)

        # Compute the max bytes to read until the end or until we reach the user requested max
        max_bytes_to_read = self._end_offset_exclusive - super(StreamSlice, self).tell()
        if size != READ_UNTIL_END:
            max_bytes_to_read = min(max_bytes_to_read, size)

        return super(StreamSlice, self).read(max_bytes_to_read)

    def _file_min(self, first, second):
        if first == READ_UNTIL_END:
            return second

        if second == READ_UNTIL_END:
            return first

        return min(first, second)

    def tell(self):
        return super(StreamSlice, self).tell() - self._start_offset

    def seek(self, index, whence=WHENCE_ABSOLUTE):
        index = self._file_min(self._end_offset_exclusive, index)
        super(StreamSlice, self).seek(index, whence)


# TODO(kleesc): Could https://werkzeug.palletsprojects.com/en/1.0.x/wsgi/#werkzeug.wsgi.LimitedStream replace this?
class LimitingStream(StreamSlice):
    """
    A file-like object which mimics the specified file stream being limited to the given number of
    bytes.

    All calls after that limit (if specified) will act as if the file has no additional data.
    """

    def __init__(self, fileobj, read_limit=READ_UNTIL_END, seekable=True):
        super(LimitingStream, self).__init__(fileobj, 0, read_limit)
        self._seekable = seekable

    def seek(self, index, whence=WHENCE_ABSOLUTE):
        if not self._seekable:
            raise AttributeError

        super(LimitingStream, self).seek(index, whence)
