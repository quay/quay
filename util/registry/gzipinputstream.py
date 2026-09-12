import string
import zlib

BLOCK_SIZE = 16384
"""Read block size"""

WINDOW_BUFFER_SIZE = 16 + zlib.MAX_WBITS
"""zlib window buffer size, set to gzip's format"""

GZIP_MAGIC = b"\x1f\x8b"
"""Leading bytes of every gzip member (RFC 1952)"""

JSON_LEAD = (b"{", b"[")
"""First non-whitespace byte of a JSON document"""

HEAD_BYTES = 32
"""How many leading bytes an UnrecognizedStreamError carries"""


class UnrecognizedStreamError(ValueError):
    """
    The stream starts with neither the gzip magic nor a JSON document.

    `head` holds the first HEAD_BYTES bytes for logging.
    """

    def __init__(self, head):
        super().__init__("stream is neither gzip nor JSON")
        self.head = head[:HEAD_BYTES]


class GzipInputStream(object):
    """
    Simple class that allow streaming reads from GZip files.

    Python 2.x gzip.GZipFile relies on .seek() and .tell(), so it
    doesn't support this (@see: http://bo4.me/YKWSsL).

    The first block decides how the stream is read, before any byte is served:
    the gzip magic means decompress; a JSON document (after optional whitespace)
    is passed through unchanged, because some storage backends (e.g. Google
    Cloud Storage) decompress objects stored with Content-Encoding: gzip on the
    way out; anything else raises UnrecognizedStreamError. `passthrough` tells
    the caller which of the first two applied. A stream that starts with the
    gzip magic but is corrupt still raises zlib.error while being read, and a
    truncated gzip stream still yields the partial payload without error.

    Adapted from: https://gist.github.com/beaufour/4205533
    """

    def __init__(self, fileobj):
        """
        Initialize with the given file-like object.

        @param fileobj: file-like object,
        """
        self._file = fileobj
        self._zip = zlib.decompressobj(WINDOW_BUFFER_SIZE)
        self._offset = 0  # position in unzipped stream

        first = self._file.read(BLOCK_SIZE)
        if first.startswith(GZIP_MAGIC):
            self.passthrough = False
            self._data = self._zip.decompress(first)
        elif first.lstrip().startswith(JSON_LEAD):
            self.passthrough = True
            self._data = first
        else:
            raise UnrecognizedStreamError(first)

    def __fill(self, num_bytes):
        """
        Fill the internal buffer with 'num_bytes' of data.

        @param num_bytes: int, number of bytes to read in (0 = everything)
        """

        if not self._zip:
            return

        while not num_bytes or len(self._data) < num_bytes:
            data = self._file.read(BLOCK_SIZE)
            if not data:
                if not self.passthrough:
                    self._data = self._data + self._zip.flush()
                self._zip = None  # no more data
                break

            if self.passthrough:
                self._data = self._data + data
            else:
                self._data = self._data + self._zip.decompress(data)

    def __iter__(self):
        return self

    def seek(self, offset, whence=0):
        if whence == 0:
            position = offset
        elif whence == 1:
            position = self._offset + offset
        else:
            raise IOError("Illegal argument")

        if position < self._offset:
            raise IOError("Cannot seek backwards")

        # skip forward, in blocks
        while position > self._offset:
            if not self.read(min(position - self._offset, BLOCK_SIZE)):
                break

    def tell(self):
        return self._offset

    def read(self, size=0):
        self.__fill(size)
        if size:
            data = self._data[:size]
            self._data = self._data[size:]
        else:
            data = self._data
            self._data = b""

        self._offset = self._offset + len(data)
        return data

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration()
        return line

    def readline(self):
        # make sure we have an entire line
        while self._zip and b"\n" not in self._data:
            self.__fill(len(self._data) + 512)

        pos = self._data.find(b"\n") + 1
        if pos <= 0:
            return self.read()

        return self.read(pos)

    def readlines(self):
        lines = []
        while True:
            line = self.readline()
            if not line:
                break

            lines.append(line)
        return lines

    def close(self):
        self._file.close()
