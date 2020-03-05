from io import BytesIO, StringIO
from util.registry.filelike import FilelikeStreamConcat, LimitingStream, StreamSlice


def somegenerator():
    yield b"some"
    yield b"cool"
    yield b"file-contents"


def test_parts():
    gens = iter([BytesIO(s) for s in somegenerator()])
    fileobj = FilelikeStreamConcat(gens)

    assert fileobj.read(2) == b"so"
    assert fileobj.read(3) == b"mec"
    assert fileobj.read(7) == b"oolfile"
    assert fileobj.read(-1) == b"-contents"


def test_entire():
    gens = iter([BytesIO(s) for s in somegenerator()])
    fileobj = FilelikeStreamConcat(gens)
    assert fileobj.read(-1) == b"somecoolfile-contents"


def test_nolimit():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj)
    assert stream.read(-1) == b"this is a cool test"
    assert len(b"this is a cool test") == stream.tell()


def test_simplelimit():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 4)
    assert stream.read(-1) == b"this"
    assert 4 == stream.tell()


def test_simplelimit_readdefined():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 4)
    assert stream.read(2) == b"th"
    assert 2 == stream.tell()


def test_nolimit_readdefined():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, -1)
    assert stream.read(2) == b"th"
    assert 2 == stream.tell()


def test_limit_multiread():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 7)
    assert stream.read(4) == b"this"
    assert stream.read(3) == b" is"
    assert stream.read(2) == b""
    assert 7 == stream.tell()


def test_limit_multiread2():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 7)
    assert stream.read(4) == b"this"
    assert stream.read(-1) == b" is"
    assert 7 == stream.tell()


def test_seek():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj)
    stream.seek(2)

    assert stream.read(2) == b"is"
    assert 4 == stream.tell()


def test_seek_withlimit():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 3)
    stream.seek(2)

    assert stream.read(2) == b"i"
    assert 3 == stream.tell()


def test_seek_pastlimit():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 3)
    stream.seek(4)

    assert stream.read(1) == b""
    assert 3 == stream.tell()


def test_seek_to_tell():
    fileobj = BytesIO(b"this is a cool test")
    stream = LimitingStream(fileobj, 3)
    stream.seek(stream.tell())

    assert stream.read(4) == b"thi"
    assert 3 == stream.tell()


def test_none_read():
    class NoneReader(object):
        def read(self, size=None):
            return None

    stream = StreamSlice(NoneReader(), 0)
    assert stream.read(-1) == None
    assert stream.tell() == 0


def test_noslice():
    fileobj = BytesIO(b"this is a cool test")
    stream = StreamSlice(fileobj, 0)
    assert stream.read(-1) == b"this is a cool test"
    assert len(b"this is a cool test") == stream.tell()


def test_startindex():
    fileobj = BytesIO(b"this is a cool test")
    stream = StreamSlice(fileobj, 5)
    assert stream.read(-1) == b"is a cool test"
    assert len(b"is a cool test") == stream.tell()


def test_startindex_limitedread():
    fileobj = BytesIO(b"this is a cool test")
    stream = StreamSlice(fileobj, 5)
    assert stream.read(4) == b"is a"
    assert 4 == stream.tell()


def test_slice():
    fileobj = BytesIO(b"this is a cool test")
    stream = StreamSlice(fileobj, 5, 9)
    assert stream.read(-1) == b"is a"
    assert len(b"is a") == stream.tell()


def test_slice_explictread():
    fileobj = BytesIO(b"this is a cool test")
    stream = StreamSlice(fileobj, 5, 9)
    assert stream.read(2) == b"is"
    assert stream.read(5) == b" a"
    assert len(b"is a") == stream.tell()
