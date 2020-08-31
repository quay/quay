import uuid

from datetime import datetime, timedelta
from contextlib import contextmanager

from prometheus_client import Counter, Gauge

from data.database import QueueItem, db, db_for_update, db_random_func
from util.morecollections import AttrDict


queue_item_puts = Counter(
    "quay_queue_item_puts_total",
    "number of items that have been added to the queue",
    labelnames=["queue_name"],
)
queue_item_gets = Counter(
    "quay_queue_item_gets_total",
    "number of times get() has been called on queue",
    labelnames=["queue_name", "availability"],
)
queue_item_deletes = Counter(
    "quay_queue_item_deletes_total", "number of expired queue items that have been deleted"
)

queue_items_locked = Gauge(
    "quay_queue_items_locked",
    "number of queue items that have been acquired",
    labelnames=["queue_name"],
)
queue_items_available = Gauge(
    "quay_queue_items_available",
    "number of queue items that have not expired",
    labelnames=["queue_name"],
)
queue_items_available_unlocked = Gauge(
    "quay_queue_items_available_unlocked",
    "number of queue items that have not expired and are not locked",
    labelnames=["queue_name"],
)


MINIMUM_EXTENSION = timedelta(seconds=20)
DEFAULT_BATCH_SIZE = 1000


class WorkQueue(object):
    """
    Work queue defines methods for interacting with a queue backed by the database.
    """

    def __init__(
        self,
        queue_name,
        transaction_factory,
        canonical_name_match_list=None,
        has_namespace=False,
    ):
        self._queue_name = queue_name
        self._transaction_factory = transaction_factory
        self._currently_processing = False
        self._has_namespaced_items = has_namespace

        if canonical_name_match_list is None:
            self._canonical_name_match_list = []
        else:
            self._canonical_name_match_list = canonical_name_match_list

    @staticmethod
    def _canonical_name(name_list):
        return "/".join(name_list) + "/"

    @classmethod
    def _running_jobs(cls, now, name_match_query):
        return cls._running_jobs_where(QueueItem.select(QueueItem.queue_name), now).where(
            QueueItem.queue_name ** name_match_query
        )

    @classmethod
    def _available_jobs(cls, now, name_match_query):
        return cls._available_jobs_where(QueueItem.select(), now).where(
            QueueItem.queue_name ** name_match_query
        )

    @staticmethod
    def _running_jobs_where(query, now):
        return query.where(QueueItem.available == False, QueueItem.processing_expires > now)

    @staticmethod
    def _available_jobs_where(query, now):
        return query.where(
            QueueItem.available_after <= now,
            ((QueueItem.available == True) | (QueueItem.processing_expires <= now)),
            QueueItem.retries_remaining > 0,
        )

    @classmethod
    def _available_jobs_not_running(cls, now, name_match_query, running_query):
        return cls._available_jobs(now, name_match_query).where(
            ~(QueueItem.queue_name << running_query)
        )

    def num_alive_jobs(self, canonical_name_list):
        """
        Returns the number of alive queue items with a given prefix.
        """

        def strip_slash(name):
            return name.lstrip("/")

        canonical_name_list = list(map(strip_slash, canonical_name_list))
        canonical_name_query = "/".join([self._queue_name] + canonical_name_list) + "%"

        return (
            QueueItem.select()
            .where(QueueItem.queue_name ** canonical_name_query)
            .where(QueueItem.retries_remaining > 0)
            .count()
        )

    def num_available_jobs_between(
        self, available_min_time, available_max_time, canonical_name_list
    ):
        """
        Returns the number of available queue items with a given prefix, between the two provided
        times.
        """

        def strip_slash(name):
            return name.lstrip("/")

        canonical_name_list = list(map(strip_slash, canonical_name_list))

        available = self._available_jobs(
            available_max_time, "/".join([self._queue_name] + canonical_name_list) + "%"
        )

        return available.where(QueueItem.available_after >= available_min_time).count()

    def _name_match_query(self):
        return "%s%%" % self._canonical_name([self._queue_name] + self._canonical_name_match_list)

    @staticmethod
    def _item_by_id_for_update(queue_id):
        return db_for_update(QueueItem.select().where(QueueItem.id == queue_id)).get()

    def get_metrics(self):
        now = datetime.utcnow()
        name_match_query = self._name_match_query()

        running_query = self._running_jobs(now, name_match_query)
        running_count = running_query.distinct().count()

        available_query = self._available_jobs(now, name_match_query)
        available_count = available_query.select(QueueItem.queue_name).distinct().count()

        available_not_running_query = self._available_jobs_not_running(
            now, name_match_query, running_query
        )
        available_not_running_count = (
            available_not_running_query.select(QueueItem.queue_name).distinct().count()
        )

        return (running_count, available_not_running_count, available_count)

    def update_metrics(self):
        (running_count, available_not_running_count, available_count) = self.get_metrics()
        queue_items_locked.labels(self._queue_name).set(running_count)
        queue_items_available.labels(self._queue_name).set(available_count)
        queue_items_available_unlocked.labels(self._queue_name).set(available_not_running_count)

    def has_retries_remaining(self, item_id):
        """
        Returns whether the queue item with the given id has any retries remaining.

        If the queue item does not exist, returns False.
        """
        with self._transaction_factory(db):
            try:
                return QueueItem.get(id=item_id).retries_remaining > 0
            except QueueItem.DoesNotExist:
                return False

    def delete_namespaced_items(self, namespace, subpath=None):
        """
        Deletes all items in this queue that exist under the given namespace.
        """
        if not self._has_namespaced_items:
            return False

        subpath_query = "%s/" % subpath if subpath else ""
        queue_prefix = "%s/%s/%s%%" % (self._queue_name, namespace, subpath_query)
        return QueueItem.delete().where(QueueItem.queue_name ** queue_prefix).execute()

    def alive(self, canonical_name_list):
        """
        Returns True if a job matching the canonical name list is currently processing or available.
        """
        canonical_name = self._canonical_name([self._queue_name] + canonical_name_list)
        try:
            select_query = QueueItem.select().where(QueueItem.queue_name == canonical_name)
            now = datetime.utcnow()

            overall_query = self._available_jobs_where(
                select_query.clone(), now
            ) | self._running_jobs_where(select_query.clone(), now)
            overall_query.get()
            return True
        except QueueItem.DoesNotExist:
            return False

    def _queue_dict(self, canonical_name_list, message, available_after, retries_remaining):
        return dict(
            queue_name=self._canonical_name([self._queue_name] + canonical_name_list),
            body=message,
            retries_remaining=retries_remaining,
            available_after=datetime.utcnow() + timedelta(seconds=available_after or 0),
        )

    @contextmanager
    def batch_insert(self, batch_size=DEFAULT_BATCH_SIZE):
        items_to_insert = []

        def batch_put(canonical_name_list, message, available_after=0, retries_remaining=5):
            """
            Put an item, if it shouldn't be processed for some number of seconds, specify that
            amount as available_after.

            Returns the ID of the queue item added.
            """
            items_to_insert.append(
                self._queue_dict(canonical_name_list, message, available_after, retries_remaining)
            )

        yield batch_put

        # Chunk the inserted items into batch_size chunks and insert_many
        remaining = list(items_to_insert)
        while remaining:
            current_batch = remaining[0:batch_size]
            QueueItem.insert_many(current_batch).execute()
            queue_item_puts.labels(self._queue_name).inc(len(current_batch))
            remaining = remaining[batch_size:]

    def put(self, canonical_name_list, message, available_after=0, retries_remaining=5):
        """
        Put an item, if it shouldn't be processed for some number of seconds, specify that amount as
        available_after.

        Returns the ID of the queue item added.
        """
        item = QueueItem.create(
            **self._queue_dict(canonical_name_list, message, available_after, retries_remaining)
        )
        queue_item_puts.labels(self._queue_name).inc()
        return str(item.id)

    def _select_available_item(self, ordering_required, now):
        """
        Selects an available queue item from the queue table and returns it, if any.

        If none, return None.
        """
        name_match_query = self._name_match_query()

        try:
            if ordering_required:
                # The previous solution to this used a select for update in a
                # transaction to prevent multiple instances from processing the
                # same queue item. This suffered performance problems. This solution
                # instead has instances attempt to update the potential queue item to be
                # unavailable. However, since their update clause is restricted to items
                # that are available=False, only one instance's update will succeed, and
                # it will have a changed row count of 1. Instances that have 0 changed
                # rows know that another instance is already handling that item.
                running = self._running_jobs(now, name_match_query)
                avail = self._available_jobs_not_running(now, name_match_query, running)
                return avail.order_by(QueueItem.id).get()
            else:
                # If we don't require ordering, we grab a random item from any of the first 50 available.
                subquery = self._available_jobs(now, name_match_query).limit(50).alias("j1")
                return (
                    QueueItem.select()
                    .join(subquery, on=QueueItem.id == subquery.c.id)
                    .order_by(db_random_func())
                    .get()
                )

        except QueueItem.DoesNotExist:
            # No available queue item was found.
            return None

    def _attempt_to_claim_item(self, db_item, now, processing_time):
        """
        Attempts to claim the specified queue item for this instance. Returns True on success and
        False on failure.

        Note that the underlying QueueItem row in the database will be changed on success, but the
        db_item object given as a parameter will *not* have its fields updated.
        """

        # Try to claim the item. We do so by updating the item's information only if its current
        # state ID matches that returned in the previous query. Since all updates to the QueueItem
        # must change the state ID, this is guarenteed to only succeed if the item has not yet been
        # claimed by another caller.
        #
        # Note that we use this method because InnoDB takes locks on *every* clause in the WHERE when
        # performing the update. Previously, we would check all these columns, resulting in a bunch
        # of lock contention. This change mitigates the problem significantly by only checking two
        # columns (id and state_id), both of which should be absolutely unique at all times.
        set_unavailable_query = QueueItem.update(
            available=False,
            processing_expires=now + timedelta(seconds=processing_time),
            retries_remaining=QueueItem.retries_remaining - 1,
            state_id=str(uuid.uuid4()),
        ).where(QueueItem.id == db_item.id, QueueItem.state_id == db_item.state_id)

        changed = set_unavailable_query.execute()
        return changed == 1

    def get(self, processing_time=300, ordering_required=False):
        """
        Get an available item and mark it as unavailable for the default of five minutes.

        The result of this method must always be composed of simple python objects which are JSON
        serializable for network portability reasons.
        """
        now = datetime.utcnow()

        # Select an available queue item.
        db_item = self._select_available_item(ordering_required, now)
        if db_item is None:
            self._currently_processing = False
            queue_item_gets.labels(self._queue_name, "nonexistant").inc()
            return None

        # Attempt to claim the item for this instance.
        was_claimed = self._attempt_to_claim_item(db_item, now, processing_time)
        if not was_claimed:
            self._currently_processing = False
            queue_item_gets.labels(self._queue_name, "claimed").inc()
            return None

        self._currently_processing = True
        queue_item_gets.labels(self._queue_name, "acquired").inc()

        # Return a view of the queue item rather than an active db object
        return AttrDict(
            {
                "id": db_item.id,
                "body": db_item.body,
                "retries_remaining": db_item.retries_remaining - 1,
            }
        )

    def cancel(self, item_id):
        """
        Attempts to cancel the queue item with the given ID from the queue.

        Returns true on success and false if the queue item could not be canceled.
        """
        count_removed = QueueItem.delete().where(QueueItem.id == item_id).execute()
        return count_removed > 0

    def complete(self, completed_item):
        self._currently_processing = not self.cancel(completed_item.id)

    def incomplete(self, incomplete_item, retry_after=300, restore_retry=False):
        with self._transaction_factory(db):
            retry_date = datetime.utcnow() + timedelta(seconds=retry_after)

            try:
                incomplete_item_obj = self._item_by_id_for_update(incomplete_item.id)
                incomplete_item_obj.available_after = retry_date
                incomplete_item_obj.available = True

                if restore_retry:
                    incomplete_item_obj.retries_remaining += 1

                incomplete_item_obj.save()
                self._currently_processing = False
                return incomplete_item_obj.retries_remaining > 0
            except QueueItem.DoesNotExist:
                return False

    def extend_processing(
        self, item, seconds_from_now, minimum_extension=MINIMUM_EXTENSION, updated_data=None
    ):
        with self._transaction_factory(db):
            try:
                queue_item = self._item_by_id_for_update(item.id)
                new_expiration = datetime.utcnow() + timedelta(seconds=seconds_from_now)
                has_change = False

                # Only actually write the new expiration to the db if it moves the expiration some minimum
                if new_expiration - queue_item.processing_expires > minimum_extension:
                    queue_item.processing_expires = new_expiration
                    has_change = True

                if updated_data is not None and queue_item.body != updated_data:
                    queue_item.body = updated_data
                    has_change = True

                if has_change:
                    queue_item.save()

                return has_change
            except QueueItem.DoesNotExist:
                return False


def delete_expired(expiration_threshold, deletion_threshold, batch_size):
    """
    Deletes all queue items that are older than the provided expiration threshold in batches of the
    provided size. If there are less items than the deletion threshold, this method does nothing.

    Returns the number of items deleted.
    """
    to_delete = list(
        QueueItem.select()
        .where(QueueItem.processing_expires <= expiration_threshold)
        .limit(batch_size)
    )

    if len(to_delete) < deletion_threshold:
        return 0

    QueueItem.delete().where(QueueItem.id << to_delete).execute()
    queue_item_deletes.inc(len(to_delete))
    return len(to_delete)
