import gzip
import json
import zlib
from io import BytesIO

import pytest

from util.registry.gzipinputstream import GzipInputStream, UnrecognizedStreamError

LOG_ENTRIES = {"logs": [{"message": "Step 1/2 : FROM scratch"}, {"message": "Done"}]}
PAYLOAD = json.dumps(LOG_ENTRIES).encode("utf-8")


class ShortReadFile:
    """File-like object that only ever hands back `chunk_size` bytes per read,
    regardless of the requested size, to simulate a short-reading backend."""

    def __init__(self, data, chunk_size=1):
        self._data = data
        self._pos = 0
        self._chunk_size = chunk_size

    def read(self, size=-1):
        end = min(self._pos + self._chunk_size, len(self._data))
        chunk = self._data[self._pos : end]
        self._pos = end
        return chunk


def test_read_gzip_stream():
    stream = GzipInputStream(BytesIO(gzip.compress(PAYLOAD)))
    assert not stream.passthrough
    assert stream.read() == PAYLOAD


def test_read_gzip_stream_in_blocks():
    stream = GzipInputStream(BytesIO(gzip.compress(PAYLOAD)))
    chunks = []
    while True:
        chunk = stream.read(7)
        if not chunk:
            break
        chunks.append(chunk)
    assert b"".join(chunks) == PAYLOAD
    assert stream.tell() == len(PAYLOAD)


def test_readlines_gzip_stream():
    lines = b"line one\nline two\nlast"
    stream = GzipInputStream(BytesIO(gzip.compress(lines)))
    assert stream.readlines() == [b"line one\n", b"line two\n", b"last"]


def test_read_already_decoded_stream():
    # Storage backends such as Google Cloud Storage apply decompressive
    # transcoding to objects stored with Content-Encoding: gzip, so the reader
    # may receive the plain payload instead of the gzip bytes. Pass it through.
    stream = GzipInputStream(BytesIO(PAYLOAD))
    assert stream.passthrough
    assert stream.read() == PAYLOAD


@pytest.mark.parametrize("payload", [b"  \n" + PAYLOAD, b"[]"])
def test_read_already_decoded_stream_json_lead(payload):
    stream = GzipInputStream(BytesIO(payload))
    assert stream.passthrough
    assert stream.read() == payload


def test_read_already_decoded_stream_in_blocks():
    stream = GzipInputStream(BytesIO(PAYLOAD))
    chunks = []
    while True:
        chunk = stream.read(5)
        if not chunk:
            break
        chunks.append(chunk)
    assert b"".join(chunks) == PAYLOAD
    assert stream.tell() == len(PAYLOAD)


@pytest.mark.parametrize("payload", [b"", b"not an archive", b"\x00" * 64])
def test_unrecognized_stream_raises_before_read(payload):
    # Neither gzip nor JSON: refuse up front so the caller can fail before
    # sending any response bytes. `head` is capped for logging.
    with pytest.raises(UnrecognizedStreamError) as excinfo:
        GzipInputStream(BytesIO(payload))
    assert excinfo.value.head == payload[:32]


def test_corrupt_gzip_raises_while_reading():
    # A stream that carries the gzip magic is trusted at construction time;
    # corrupt bytes after it still surface as zlib.error during the read.
    with pytest.raises(zlib.error):
        GzipInputStream(BytesIO(b"\x1f\x8bnot really gzip")).read()


def test_gzip_magic_split_across_short_reads():
    # A backend that hands back only 1 byte per read (e.g. only b"\x1f" on the
    # first call) must not be misclassified as neither gzip nor JSON.
    stream = GzipInputStream(ShortReadFile(gzip.compress(PAYLOAD), chunk_size=1))
    assert not stream.passthrough
    assert stream.read() == PAYLOAD


def test_json_lead_split_across_short_reads():
    # Leading whitespace served 1 byte at a time must not be misclassified
    # before the '{' that would resolve it as JSON has arrived.
    payload = b"  \n" + PAYLOAD
    stream = GzipInputStream(ShortReadFile(payload, chunk_size=1))
    assert stream.passthrough
    assert stream.read() == payload


def test_truncated_gzip_yields_partial_payload():
    # Truncation is not detected: zlib returns what it could inflate and
    # flush() does not complain about a missing trailer. Unchanged behaviour.
    full = gzip.compress(b"x" * 100000)
    data = GzipInputStream(BytesIO(full[: len(full) // 2])).read()
    assert 0 < len(data) < 100000
