from io import StringIO
from util.registry.filelike import FilelikeStreamConcat, LimitingStream, StreamSlice


def somegenerator():
    yield "some"
    yield "cool"
    yield "file-contents"


def test_parts():
    gens = iter([StringIO(s) for s in somegenerator()])
    fileobj = FilelikeStreamConcat(gens)

    assert fileobj.read(2) == "so"
    assert fileobj.read(3) == "mec"
    assert fileobj.read(7) == "oolfile"
    assert fileobj.read(-1) == "-contents"


def test_entire():
    gens = iter([StringIO(s) for s in somegenerator()])
    fileobj = FilelikeStreamConcat(gens)
    assert fileobj.read(-1) == "somecoolfile-contents"


def test_nolimit():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj)
    assert stream.read(-1) == "this is a cool test"
    assert len("this is a cool test") == stream.tell()


def test_simplelimit():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 4)
    assert stream.read(-1) == "this"
    assert 4 == stream.tell()


def test_simplelimit_readdefined():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 4)
    assert stream.read(2) == "th"
    assert 2 == stream.tell()


def test_nolimit_readdefined():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, -1)
    assert stream.read(2) == "th"
    assert 2 == stream.tell()


def test_limit_multiread():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 7)
    assert stream.read(4) == "this"
    assert stream.read(3) == " is"
    assert stream.read(2) == ""
    assert 7 == stream.tell()


def test_limit_multiread2():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 7)
    assert stream.read(4) == "this"
    assert stream.read(-1) == " is"
    assert 7 == stream.tell()


def test_seek():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj)
    stream.seek(2)

    assert stream.read(2) == "is"
    assert 4 == stream.tell()


def test_seek_withlimit():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 3)
    stream.seek(2)

    assert stream.read(2) == "i"
    assert 3 == stream.tell()


def test_seek_pastlimit():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 3)
    stream.seek(4)

    assert stream.read(1) == ""
    assert 3 == stream.tell()


def test_seek_to_tell():
    fileobj = StringIO("this is a cool test")
    stream = LimitingStream(fileobj, 3)
    stream.seek(stream.tell())

    assert stream.read(4) == "thi"
    assert 3 == stream.tell()


def test_none_read():
    class NoneReader(object):
        def read(self, size=None):
            return None

    stream = StreamSlice(NoneReader(), 0)
    assert stream.read(-1) == None
    assert stream.tell() == 0


def test_noslice():
    fileobj = StringIO("this is a cool test")
    stream = StreamSlice(fileobj, 0)
    assert stream.read(-1) == "this is a cool test"
    assert len("this is a cool test") == stream.tell()


def test_startindex():
    fileobj = StringIO("this is a cool test")
    stream = StreamSlice(fileobj, 5)
    assert stream.read(-1) == "is a cool test"
    assert len("is a cool test") == stream.tell()


def test_startindex_limitedread():
    fileobj = StringIO("this is a cool test")
    stream = StreamSlice(fileobj, 5)
    assert stream.read(4) == "is a"
    assert 4 == stream.tell()


def test_slice():
    fileobj = StringIO("this is a cool test")
    stream = StreamSlice(fileobj, 5, 9)
    assert stream.read(-1) == "is a"
    assert len("is a") == stream.tell()


def test_slice_explictread():
    fileobj = StringIO("this is a cool test")
    stream = StreamSlice(fileobj, 5, 9)
    assert stream.read(2) == "is"
    assert stream.read(5) == " a"
    assert len("is a") == stream.tell()
