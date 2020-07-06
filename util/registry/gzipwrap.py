from gzip import GzipFile

# 256K buffer to Gzip
GZIP_BUFFER_SIZE = 1024 * 256


class GzipWrap(object):
    def __init__(self, input, filename=None, compresslevel=1):
        self.input = iter(input)
        self.buffer = b""
        self.zipper = GzipFile(
            filename, mode="wb", fileobj=self, compresslevel=compresslevel, mtime=0
        )
        self.is_done = False

    def read(self, size=-1):
        if size is None or size < 0:
            raise Exception("Call to GzipWrap with unbound size will result in poor performance")

        # If the buffer already has enough bytes, then simply pop them off of
        # the beginning and return them.
        if len(self.buffer) >= size or self.is_done:
            ret = self.buffer[0:size]
            self.buffer = self.buffer[size:]
            return ret

        # Otherwise, zip the input until we have enough bytes.
        while True:
            # Attempt to retrieve the next bytes to write.
            is_done = False

            input_size = 0
            input_buffer = b""
            while input_size < GZIP_BUFFER_SIZE:
                try:
                    s = next(self.input)
                    input_buffer += s
                    input_size = input_size + len(s)
                except StopIteration:
                    is_done = True
                    break

            self.zipper.write(input_buffer)

            if is_done:
                self.zipper.flush()
                self.zipper.close()
                self.is_done = True

            if len(self.buffer) >= size or is_done:
                ret = self.buffer[0:size]
                self.buffer = self.buffer[size:]
                return ret

    def flush(self):
        pass

    def write(self, data):
        self.buffer += data

    def close(self):
        self.input.close()
