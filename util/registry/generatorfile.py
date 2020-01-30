def _complain_ifclosed(closed):
    if closed:
        raise ValueError("I/O operation on closed file")


class GeneratorFile(object):
    """
    File-like object which wraps a Python generator to produce the file contents.

    Modeled on StringIO and comments on the file-like interface copied from there.
    """

    def __init__(self, generator):
        self._generator = generator
        self._closed = False
        self._buf = b""
        self._position = 0

    def __iter__(self):
        return self

    def tell(self):
        """
        Return the file's current position, like stdio's ftell().
        """
        _complain_ifclosed(self._closed)
        return self._position

    def __next__(self):
        """
        A file object is its own iterator, for example iter(f) returns f (unless f is closed).

        When a file is used as an iterator, typically in a for loop (for example, for line in f:
        print line), the next() method is called repeatedly. This method returns the next input
        line, or raises StopIteration when EOF is hit.
        """
        _complain_ifclosed(self._closed)
        r = self.read()
        if not r:
            raise StopIteration
        return r

    def readable(self):
        return not self._closed

    def readline(self):
        buf = []
        while True:
            c = self.read(size=1)
            buf.append(c)
            if c == b"\n" or c == b"":
                return b"".join(buf)

    def flush(self):
        _complain_ifclosed(self._closed)

    def read(self, size=-1):
        """
        Read at most size bytes from the file (less if the read hits EOF before obtaining size
        bytes).

        If the size argument is negative or omitted, read all data until EOF is reached. The bytes
        are returned as a string object. An empty string is returned when EOF is encountered
        immediately.
        """
        _complain_ifclosed(self._closed)
        buf = self._buf
        while size < 0 or len(buf) < size:
            try:
                buf = buf + next(self._generator)
            except StopIteration:
                break

        returned = b""
        if size >= 1:
            self._buf = buf[size:]
            returned = buf[:size]
        else:
            self._buf = b""
            returned = buf

        self._position = self._position + len(returned)
        return returned

    def seek(self):
        raise NotImplementedError

    def close(self):
        self._closed = True
        del self._buf

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._closed = True
