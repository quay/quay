"""
Defines utility methods for working with gzip streams.
"""

import zlib
import time

# Window size for decompressing GZIP streams.
# This results in ZLIB automatically detecting the GZIP headers.
# http://stackoverflow.com/questions/3122145/zlib-error-error-3-while-decompressing-incorrect-header-check/22310760#22310760
ZLIB_GZIP_WINDOW = zlib.MAX_WBITS | 32

CHUNK_SIZE = 5 * 1024 * 1024


class SizeInfo(object):
    def __init__(self):
        self.uncompressed_size = 0
        self.compressed_size = 0
        self.is_valid = True


def calculate_size_handler():
    """
    Returns an object and a SocketReader handler.

    The handler will gunzip the data it receives, adding the size found to the object.
    """

    size_info = SizeInfo()
    decompressor = zlib.decompressobj(ZLIB_GZIP_WINDOW)

    def fn(buf):
        if not size_info.is_valid:
            return

        # Note: We set a maximum CHUNK_SIZE to prevent the decompress from taking too much
        # memory. As a result, we have to loop until the unconsumed tail is empty.
        current_data = buf
        size_info.compressed_size += len(current_data)

        while len(current_data) > 0:
            try:
                size_info.uncompressed_size += len(
                    decompressor.decompress(current_data, CHUNK_SIZE)
                )
            except:
                # The gzip stream is not valid for some reason.
                size_info.uncompressed_size = None
                size_info.is_valid = False
                return

            current_data = decompressor.unconsumed_tail

            # Make sure we allow the scheduler to do other work if we get stuck in this tight loop.
            if len(current_data) > 0:
                time.sleep(0)

    return size_info, fn
