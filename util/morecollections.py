class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def deep_copy(cls, attr_dict):
        copy = AttrDict(attr_dict)
        for key, value in list(copy.items()):
            if isinstance(value, AttrDict):
                copy[key] = cls.deep_copy(value)
        return copy


class FastIndexList(object):
    """
    List which keeps track of the indicies of its items in a fast manner, and allows for quick
    removal of items.
    """

    def __init__(self):
        self._list = []
        self._index_map = {}
        self._index_offset = 0
        self._counter = 0

    def add(self, item):
        """
        Adds an item to the index list.
        """
        self._list.append(item)
        self._index_map[item] = self._counter
        self._counter = self._counter + 1

    def values(self):
        """
        Returns an iterable stream of all the values in the list.
        """
        return list(self._list)

    def index(self, value):
        """
        Returns the index of the given item in the list or None if none.
        """
        found = self._index_map.get(value, None)
        if found is None:
            return None

        return found - self._index_offset

    def pop_until(self, index_inclusive):
        """
        Pops off any items in the list until the given index, inclusive, and returns them.
        """
        values = self._list[0 : index_inclusive + 1]
        for value in values:
            self._index_map.pop(value, None)

        self._index_offset = self._index_offset + index_inclusive + 1
        self._list = self._list[index_inclusive + 1 :]
        return values


class IndexedStreamingDiffTracker(object):
    """
    Helper class which tracks the difference between two streams of strings, calling the `added`
    callback for strings when they are successfully verified as being present in the first stream
    and not present in the second stream.

    Unlike StreamingDiffTracker, this class expects each string value to have an associated `index`
    value, which must be the same for equal values in both streams and *must* be in order. This
    allows us to be a bit more efficient in clearing up items that we know won't be present. The
    `index` is *not* assumed to start at 0 or be contiguous, merely increasing.
    """

    def __init__(self, reporter, result_per_stream):
        self._reporter = reporter
        self._reports_per_stream = result_per_stream
        self._new_stream_finished = False
        self._old_stream_finished = False

        self._new_stream = []
        self._old_stream = []

        self._new_stream_map = {}
        self._old_stream_map = {}

    def push_new(self, stream_tuples):
        """
        Pushes a list of values for the `New` stream.
        """
        stream_tuples_list = list(stream_tuples)
        assert len(stream_tuples_list) <= self._reports_per_stream

        if len(stream_tuples_list) < self._reports_per_stream:
            self._new_stream_finished = True

        for (item, index) in stream_tuples_list:
            if self._new_stream:
                assert index > self._new_stream[-1].index

            self._new_stream_map[index] = item
            self._new_stream.append(AttrDict(item=item, index=index))

        self._process()

    def push_old(self, stream_tuples):
        """
        Pushes a list of values for the `Old` stream.
        """
        if self._new_stream_finished and not self._new_stream:
            # Nothing more to do.
            return

        stream_tuples_list = list(stream_tuples)
        assert len(stream_tuples_list) <= self._reports_per_stream

        if len(stream_tuples_list) < self._reports_per_stream:
            self._old_stream_finished = True

        for (item, index) in stream_tuples:
            if self._old_stream:
                assert index > self._old_stream[-1].index

            self._old_stream_map[index] = item
            self._old_stream.append(AttrDict(item=item, index=index))

        self._process()

    def done(self):
        self._old_stream_finished = True
        self._process()

    def _process(self):
        # Process any new items that can be reported.
        old_lower_bound = self._old_stream[0].index if self._old_stream else -1
        for item_info in self._new_stream:
            # If the new item's index <= the old_lower_bound, then we know
            # we can check the old item map for it.
            if item_info.index <= old_lower_bound or self._old_stream_finished:
                if self._old_stream_map.get(item_info.index, None) is None:
                    self._reporter(item_info.item)

                # Remove the item from the map.
                self._new_stream_map.pop(item_info.index, None)

        # Rebuild the new stream list (faster than just removing).
        self._new_stream = [
            item_info for item_info in self._new_stream if self._new_stream_map.get(item_info.index)
        ]

        # Process any old items that can be removed.
        new_lower_bound = self._new_stream[0].index if self._new_stream else -1
        for item_info in list(self._old_stream):
            # Any items with indexes below the new lower bound can be removed,
            # as any comparison from the new stream was done above.
            if item_info.index < new_lower_bound:
                self._old_stream_map.pop(item_info.index, None)

        # Rebuild the old stream list (faster than just removing).
        self._old_stream = [
            item_info for item_info in self._old_stream if self._old_stream_map.get(item_info.index)
        ]


class StreamingDiffTracker(object):
    """
    Helper class which tracks the difference between two streams of strings, calling the `added`
    callback for strings when they are successfully verified as being present in the first stream
    and not present in the second stream.

    This class requires that the streams of strings be consistently ordered *in some way common to
    both* (but the strings themselves do not need to be sorted).
    """

    def __init__(self, reporter, result_per_stream):
        self._reporter = reporter
        self._reports_per_stream = result_per_stream
        self._old_stream_finished = False

        self._old_stream = FastIndexList()
        self._new_stream = FastIndexList()

    def done(self):
        self._old_stream_finished = True
        self.push_new([])

    def push_new(self, stream_values):
        """
        Pushes a list of values for the `New` stream.
        """

        # Add all the new values to the list.
        counter = 0
        for value in stream_values:
            self._new_stream.add(value)
            counter = counter + 1

        assert counter <= self._reports_per_stream

        # Process them all to see if anything has changed.
        for value in list(self._new_stream.values()):
            old_index = self._old_stream.index(value)
            if old_index is not None:
                # The item is present, so we cannot report it. However, since we've reached this point,
                # all items *before* this item in the `Old` stream are no longer necessary, so we can
                # throw them out, along with this item.
                self._old_stream.pop_until(old_index)
            else:
                # If the old stream has completely finished, then we can report, knowing no more old
                # information will be present.
                if self._old_stream_finished:
                    self._reporter(value)
                    self._new_stream.pop_until(self._new_stream.index(value))

    def push_old(self, stream_values):
        """
        Pushes a stream of values for the `Old` stream.
        """

        if self._old_stream_finished:
            return

        value_list = list(stream_values)
        assert len(value_list) <= self._reports_per_stream

        for value in value_list:
            # If the value exists in the new stream somewhere, then we know that all items *before*
            # that index in the new stream will not be in the old stream, so we can report them. We can
            # also remove the matching `New` item, as it is clearly in both streams.
            new_index = self._new_stream.index(value)
            if new_index is not None:
                # Report all items up to the current item.
                for item in self._new_stream.pop_until(new_index - 1):
                    self._reporter(item)

                # Remove the current item from the new stream.
                self._new_stream.pop_until(0)
            else:
                # This item may be seen later. Add it to the old stream set.
                self._old_stream.add(value)

        # Check to see if the `Old` stream has finished.
        if len(value_list) < self._reports_per_stream:
            self._old_stream_finished = True
