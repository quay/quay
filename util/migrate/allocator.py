import logging
import random

from bintrees import RBTree
from threading import Event


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NoAvailableKeysError(ValueError):
    pass


class CompletedKeys(object):
    def __init__(self, max_index, min_index=0):
        self._max_index = max_index
        self._min_index = min_index
        self.num_remaining = max_index - min_index
        self._slabs = RBTree()

    def _get_previous_or_none(self, index):
        try:
            return self._slabs.floor_item(index)
        except KeyError:
            return None

    def is_available(self, index):
        logger.debug("Testing index %s", index)
        if index >= self._max_index or index < self._min_index:
            logger.debug("Index out of range")
            return False

        try:
            prev_start, prev_length = self._slabs.floor_item(index)
            logger.debug("Prev range: %s-%s", prev_start, prev_start + prev_length)
            return (prev_start + prev_length) <= index
        except KeyError:
            return True

    def mark_completed(self, start_index, past_last_index):
        logger.debug("Marking the range completed: %s-%s", start_index, past_last_index)
        num_completed = min(past_last_index, self._max_index) - max(start_index, self._min_index)

        # Find the item directly before this and see if there is overlap
        to_discard = set()
        try:
            prev_start, prev_length = self._slabs.floor_item(start_index)
            max_prev_completed = prev_start + prev_length
            if max_prev_completed >= start_index:
                # we are going to merge with the range before us
                logger.debug(
                    "Merging with the prev range: %s-%s", prev_start, prev_start + prev_length
                )
                to_discard.add(prev_start)
                num_completed = max(num_completed - (max_prev_completed - start_index), 0)
                start_index = prev_start
                past_last_index = max(past_last_index, prev_start + prev_length)
        except KeyError:
            pass

        # Find all keys between the start and last index and merge them into one block
        for merge_start, merge_length in self._slabs.iter_items(start_index, past_last_index + 1):
            if merge_start in to_discard:
                logger.debug(
                    "Already merged with block %s-%s", merge_start, merge_start + merge_length
                )
                continue

            candidate_next_index = merge_start + merge_length
            logger.debug("Merging with block %s-%s", merge_start, candidate_next_index)
            num_completed -= merge_length - max(candidate_next_index - past_last_index, 0)
            to_discard.add(merge_start)
            past_last_index = max(past_last_index, candidate_next_index)

        # write the new block which is fully merged
        discard = False
        if past_last_index >= self._max_index:
            logger.debug("Discarding block and setting new max to: %s", start_index)
            self._max_index = start_index
            discard = True

        if start_index <= self._min_index:
            logger.debug("Discarding block and setting new min to: %s", past_last_index)
            self._min_index = past_last_index
            discard = True

        if to_discard:
            logger.debug("Discarding %s obsolete blocks", len(to_discard))
            self._slabs.remove_items(to_discard)

        if not discard:
            logger.debug("Writing new block with range: %s-%s", start_index, past_last_index)
            self._slabs.insert(start_index, past_last_index - start_index)

        # Update the number of remaining items with the adjustments we've made
        assert num_completed >= 0
        self.num_remaining -= num_completed
        logger.debug("Total blocks: %s", len(self._slabs))

    def get_block_start_index(self, block_size_estimate):
        logger.debug("Total range: %s-%s", self._min_index, self._max_index)
        if self._max_index <= self._min_index:
            raise NoAvailableKeysError("All indexes have been marked completed")

        num_holes = len(self._slabs) + 1
        random_hole = random.randint(0, num_holes - 1)
        logger.debug("Selected random hole %s with %s total holes", random_hole, num_holes)

        hole_start = self._min_index
        past_hole_end = self._max_index

        # Now that we have picked a hole, we need to define the bounds
        if random_hole > 0:
            # There will be a slab before this hole, find where it ends
            bound_entries = self._slabs.nsmallest(random_hole + 1)[-2:]
            left_index, left_len = bound_entries[0]
            logger.debug("Left range %s-%s", left_index, left_index + left_len)
            hole_start = left_index + left_len

            if len(bound_entries) > 1:
                right_index, right_len = bound_entries[1]
                logger.debug("Right range %s-%s", right_index, right_index + right_len)
                past_hole_end, _ = bound_entries[1]
        elif not self._slabs.is_empty():
            right_index, right_len = self._slabs.nsmallest(1)[0]
            logger.debug("Right range %s-%s", right_index, right_index + right_len)
            past_hole_end, _ = self._slabs.nsmallest(1)[0]

        # Now that we have our hole bounds, select a random block from [0:len - block_size_estimate]
        logger.debug("Selecting from hole range: %s-%s", hole_start, past_hole_end)
        rand_max_bound = max(hole_start, past_hole_end - block_size_estimate)
        logger.debug("Rand max bound: %s", rand_max_bound)
        return random.randint(hole_start, rand_max_bound)


def yield_random_entries(batch_query, primary_key_field, batch_size, max_id, min_id=0):
    """
    This method will yield items from random blocks in the database.

    We will track metadata about which keys are available for work, and we will complete the
    backfill when there is no more work to be done. The method yields tuples of (candidate, Event),
    and if the work was already done by another worker, the caller should set the event. Batch
    candidates must have an "id" field which can be inspected.
    """

    min_id = max(min_id, 0)
    max_id = max(max_id, 1)
    allocator = CompletedKeys(max_id + 1, min_id)

    try:
        while True:
            start_index = allocator.get_block_start_index(batch_size)
            end_index = min(start_index + batch_size, max_id + 1)
            all_candidates = list(
                batch_query()
                .where(primary_key_field >= start_index, primary_key_field < end_index)
                .order_by(primary_key_field)
            )

            if len(all_candidates) == 0:
                logger.info(
                    "No candidates, marking entire block completed %s-%s", start_index, end_index
                )
                allocator.mark_completed(start_index, end_index)
                continue

            logger.info("Found %s candidates, processing block", len(all_candidates))
            batch_completed = 0
            for candidate in all_candidates:
                abort_early = Event()
                yield candidate, abort_early, allocator.num_remaining - batch_completed
                batch_completed += 1
                if abort_early.is_set():
                    logger.info("Overlap with another worker, aborting")
                    break

            completed_through = candidate.id + 1
            logger.info("Marking id range as completed: %s-%s", start_index, completed_through)
            allocator.mark_completed(start_index, completed_through)

    except NoAvailableKeysError:
        logger.info("No more work")
