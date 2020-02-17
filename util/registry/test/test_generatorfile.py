from _pyio import BufferedReader

import magic

from util.registry.generatorfile import GeneratorFile


def sample_generator():
    yield "this"
    yield "is"
    yield "a"
    yield "test"


def test_basic_generator():
    with GeneratorFile(sample_generator()) as f:
        assert f.tell() == 0
        assert f.read() == "thisisatest"
        assert f.tell() == len("thisisatest")


def test_same_lengths():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(4) == "this"
        assert f.tell() == 4

        assert f.read(2) == "is"
        assert f.tell() == 6

        assert f.read(1) == "a"
        assert f.tell() == 7

        assert f.read(4) == "test"
        assert f.tell() == 11


def test_indexed_lengths():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(6) == "thisis"
        assert f.tell() == 6

        assert f.read(5) == "atest"
        assert f.tell() == 11


def test_misindexed_lengths():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(6) == "thisis"
        assert f.tell() == 6

        assert f.read(3) == "ate"
        assert f.tell() == 9

        assert f.read(2) == "st"
        assert f.tell() == 11

        assert f.read(2) == ""
        assert f.tell() == 11


def test_misindexed_lengths_2():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(8) == "thisisat"
        assert f.tell() == 8

        assert f.read(1) == "e"
        assert f.tell() == 9

        assert f.read(2) == "st"
        assert f.tell() == 11

        assert f.read(2) == ""
        assert f.tell() == 11


def test_overly_long():
    with GeneratorFile(sample_generator()) as f:
        assert f.read(60) == "thisisatest"
        assert f.tell() == 11


def test_with_bufferedreader():
    with GeneratorFile(sample_generator()) as f:
        buffered = BufferedReader(f)
        assert buffered.peek(10) == "thisisatest"
        assert buffered.read(10) == "thisisates"


def mimed_html_generator():
    yield "<html>"
    yield "<body>"
    yield "sometext" * 1024
    yield "</body>"
    yield "</html>"


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
