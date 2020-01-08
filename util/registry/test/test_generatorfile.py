from _pyio import BufferedReader, TextIOWrapper

import magic

from util.registry.generatorfile import GeneratorFile


def sample_generator():
    yield b"this"
    yield b"is"
    yield b"a"
    yield b"test"


def test_basic_generator():
    with GeneratorFile(sample_generator()) as f:
        assert f.tell() == 0
        assert f.read() == b"thisisatest"
        assert f.tell() == len(b"thisisatest")


def test_same_lengths():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(4) == b"this"
        assert f.tell() == 4

        assert f.read(2) == b"is"
        assert f.tell() == 6

        assert f.read(1) == b"a"
        assert f.tell() == 7

        assert f.read(4) == b"test"
        assert f.tell() == 11


def test_indexed_lengths():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(6) == b"thisis"
        assert f.tell() == 6

        assert f.read(5) == b"atest"
        assert f.tell() == 11


def test_misindexed_lengths():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(6) == b"thisis"
        assert f.tell() == 6

        assert f.read(3) == b"ate"
        assert f.tell() == 9

        assert f.read(2) == b"st"
        assert f.tell() == 11

        assert f.read(2) == b""
        assert f.tell() == 11


def test_misindexed_lengths_2():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(8) == b"thisisat"
        assert f.tell() == 8

        assert f.read(1) == b"e"
        assert f.tell() == 9

        assert f.read(2) == b"st"
        assert f.tell() == 11

        assert f.read(2) == b""
        assert f.tell() == 11


def test_overly_long():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(60) == b"thisisatest"
        assert f.tell() == 11


def test_with_bufferedreader():
    with GeneratorFile(sample_generator()) as f:
        buffered = BufferedReader(f)
        assert buffered.peek(10) == b"thisisatest"
        assert buffered.read(10) == b"thisisates"


def mimed_html_generator():
    yield b"<html>"
    yield b"<body>"
    yield b"sometext" * 1024
    yield b"</body>"
    yield b"</html>"


def test_magic():
    mgc = magic.Magic(mime=True)

    with GeneratorFile(mimed_html_generator()) as f:
        buffered = BufferedReader(f)
        file_header_bytes = buffered.peek(1024)
        assert mgc.from_buffer(file_header_bytes) == "text/html"

    with GeneratorFile(sample_generator()) as f:
        buffered = BufferedReader(f)
        file_header_bytes = buffered.peek(1024)
        assert mgc.from_buffer(file_header_bytes) == "text/plain"
