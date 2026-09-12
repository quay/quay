import gzip
import json
from io import BytesIO

from util.registry.gzipinputstream import GzipInputStream

LOG_ENTRIES = {"logs": [{"message": "Step 1/2 : FROM scratch"}, {"message": "Done"}]}
PAYLOAD = json.dumps(LOG_ENTRIES).encode("utf-8")


def test_read_gzip_stream():
    stream = GzipInputStream(BytesIO(gzip.compress(PAYLOAD)))
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
    assert stream.read() == PAYLOAD


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


def test_read_empty_stream():
    assert GzipInputStream(BytesIO(b"")).read() == b""
