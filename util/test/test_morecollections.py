from util.morecollections import FastIndexList, StreamingDiffTracker, IndexedStreamingDiffTracker


def test_fastindexlist_basic_usage():
    indexlist = FastIndexList()

    # Add 1
    indexlist.add(1)
    assert list(indexlist.values()) == [1]
    assert indexlist.index(1) == 0

    # Add 2
    indexlist.add(2)
    assert list(indexlist.values()) == [1, 2]
    assert indexlist.index(1) == 0
    assert indexlist.index(2) == 1

    # Pop nothing.
    indexlist.pop_until(-1)
    assert list(indexlist.values()) == [1, 2]
    assert indexlist.index(1) == 0
    assert indexlist.index(2) == 1

    # Pop 1.
    assert indexlist.pop_until(0) == [1]
    assert list(indexlist.values()) == [2]
    assert indexlist.index(1) is None
    assert indexlist.index(2) == 0

    # Add 3.
    indexlist.add(3)
    assert list(indexlist.values()) == [2, 3]
    assert indexlist.index(2) == 0
    assert indexlist.index(3) == 1

    # Pop 2, 3.
    assert indexlist.pop_until(1) == [2, 3]
    assert list(indexlist.values()) == []
    assert indexlist.index(1) is None
    assert indexlist.index(2) is None
    assert indexlist.index(3) is None


def test_fastindexlist_popping():
    indexlist = FastIndexList()
    indexlist.add("hello")
    indexlist.add("world")
    indexlist.add("you")
    indexlist.add("rock")

    assert indexlist.index("hello") == 0
    assert indexlist.index("world") == 1
    assert indexlist.index("you") == 2
    assert indexlist.index("rock") == 3

    indexlist.pop_until(1)
    assert indexlist.index("you") == 0
    assert indexlist.index("rock") == 1


def test_indexedstreamingdifftracker_basic():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 3)
    tracker.push_new([("a", 0), ("b", 1), ("c", 2)])
    tracker.push_old([("b", 1)])
    tracker.done()

    assert added == ["a", "c"]


def test_indexedstreamingdifftracker_multiple_done():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 3)
    tracker.push_new([("a", 0), ("b", 1), ("c", 2)])
    tracker.push_old([("b", 1)])
    tracker.done()
    tracker.done()

    assert added == ["a", "c"]


def test_indexedstreamingdifftracker_same_streams():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 3)
    tracker.push_new([("a", 0), ("b", 1), ("c", 2)])
    tracker.push_old([("a", 0), ("b", 1), ("c", 2)])
    tracker.done()

    assert added == []


def test_indexedstreamingdifftracker_only_new():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 3)
    tracker.push_new([("a", 0), ("b", 1), ("c", 2)])
    tracker.push_old([])
    tracker.done()

    assert added == ["a", "b", "c"]


def test_indexedstreamingdifftracker_pagination():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 2)
    tracker.push_new([("a", 0), ("b", 1)])
    tracker.push_old([])

    tracker.push_new([("c", 2)])
    tracker.push_old([])

    tracker.done()

    assert added == ["a", "b", "c"]


def test_indexedstreamingdifftracker_old_pagination_no_repeat():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 2)
    tracker.push_new([("new1", 3), ("new2", 4)])
    tracker.push_old([("old1", 1), ("old2", 2)])

    tracker.push_new([])
    tracker.push_old([("new1", 3)])

    tracker.done()

    assert added == ["new2"]


def test_indexedstreamingdifftracker_old_pagination():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 2)
    tracker.push_new([("a", 10), ("b", 11)])
    tracker.push_old([("z", 1), ("y", 2)])

    tracker.push_new([("c", 12)])
    tracker.push_old([("a", 10)])

    tracker.done()

    assert added == ["b", "c"]


def test_indexedstreamingdifftracker_very_offset():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 2)
    tracker.push_new([("a", 10), ("b", 11)])
    tracker.push_old([("z", 1), ("y", 2)])

    tracker.push_new([("c", 12), ("d", 13)])
    tracker.push_old([("x", 3), ("w", 4)])

    tracker.push_new([("e", 14)])
    tracker.push_old([("a", 10), ("d", 13)])

    tracker.done()

    assert added == ["b", "c", "e"]


def test_indexedstreamingdifftracker_many_old():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 2)
    tracker.push_new([("z", 26), ("hello", 100)])
    tracker.push_old([("a", 1), ("b", 2)])

    tracker.push_new([])
    tracker.push_old([("c", 1), ("d", 2)])

    tracker.push_new([])
    tracker.push_old([("e", 3), ("f", 4)])

    tracker.push_new([])
    tracker.push_old([("g", 5), ("z", 26)])

    tracker.done()

    assert added == ["hello"]


def test_indexedstreamingdifftracker_high_old_bound():
    added = []

    tracker = IndexedStreamingDiffTracker(added.append, 2)
    tracker.push_new([("z", 26), ("hello", 100)])
    tracker.push_old([("end1", 999), ("end2", 1000)])

    tracker.push_new([])
    tracker.push_old([])

    tracker.done()

    assert added == ["z", "hello"]


def test_streamingdifftracker_basic():
    added = []

    tracker = StreamingDiffTracker(added.append, 3)
    tracker.push_new(["a", "b", "c"])
    tracker.push_old(["b"])
    tracker.done()

    assert added == ["a", "c"]


def test_streamingdifftracker_same_streams():
    added = []

    tracker = StreamingDiffTracker(added.append, 3)
    tracker.push_new(["a", "b", "c"])
    tracker.push_old(["a", "b", "c"])
    tracker.done()

    assert added == []


def test_streamingdifftracker_some_new():
    added = []

    tracker = StreamingDiffTracker(added.append, 5)
    tracker.push_new(["a", "b", "c", "d", "e"])
    tracker.push_old(["a", "b", "c"])
    tracker.done()

    assert added == ["d", "e"]


def test_streamingdifftracker_offset_new():
    added = []

    tracker = StreamingDiffTracker(added.append, 5)
    tracker.push_new(["b", "c", "d", "e"])
    tracker.push_old(["a", "b", "c"])
    tracker.done()

    assert added == ["d", "e"]


def test_streamingdifftracker_multiple_calls():
    added = []

    tracker = StreamingDiffTracker(added.append, 3)
    tracker.push_new(["a", "b", "c"])
    tracker.push_old(["b", "d", "e"])

    tracker.push_new(["f", "g", "h"])
    tracker.push_old(["g", "h"])
    tracker.done()

    assert added == ["a", "c", "f"]


def test_streamingdifftracker_empty_old():
    added = []

    tracker = StreamingDiffTracker(added.append, 3)
    tracker.push_new(["a", "b", "c"])
    tracker.push_old([])

    tracker.push_new(["f", "g", "h"])
    tracker.push_old([])
    tracker.done()

    assert added == ["a", "b", "c", "f", "g", "h"]


def test_streamingdifftracker_more_old():
    added = []

    tracker = StreamingDiffTracker(added.append, 2)
    tracker.push_new(["c", "d"])
    tracker.push_old(["a", "b"])

    tracker.push_new([])
    tracker.push_old(["c"])
    tracker.done()

    assert added == ["d"]


def test_streamingdifftracker_more_new():
    added = []

    tracker = StreamingDiffTracker(added.append, 4)
    tracker.push_new(["a", "b", "c", "d"])
    tracker.push_old(["r"])

    tracker.push_new(["e", "f", "r", "z"])
    tracker.push_old([])
    tracker.done()

    assert added == ["a", "b", "c", "d", "e", "f", "z"]


def test_streamingdifftracker_more_new2():
    added = []

    tracker = StreamingDiffTracker(added.append, 4)
    tracker.push_new(["a", "b", "c", "d"])
    tracker.push_old(["r"])

    tracker.push_new(["e", "f", "g", "h"])
    tracker.push_old([])

    tracker.push_new(["i", "j", "r", "z"])
    tracker.push_old([])
    tracker.done()

    assert added == ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "z"]
