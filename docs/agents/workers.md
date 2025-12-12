# Workers & Background Jobs

## Overview

Quay uses a worker system for background processing tasks such as garbage collection, log rotation, security scanning notifications, and storage replication. Workers operate independently of the main Flask application and process jobs either periodically or from a database-backed queue.

**Two worker types:**
- **Periodic Workers** - Execute operations on a fixed interval (e.g., cleanup, metrics refresh)
- **Queue Workers** - Process jobs from a database-backed queue (e.g., GC, replication)

## Worker Architecture

### Base Worker Class

The `Worker` base class provides scheduling infrastructure using APScheduler's `BackgroundScheduler`.

See: `workers/worker.py:59-194`

| Component | Purpose |
|-----------|---------|
| `BackgroundScheduler` | Schedules periodic operations |
| Signal handling | Graceful shutdown on SIGTERM/SIGINT |
| Sentry integration | Error tracking (when configured) |
| `Event` primitives | Coordinates shutdown (`_stop`, `_terminated`) |

### Lifecycle Methods

| Method | Purpose |
|--------|---------|
| `start()` | Initialize scheduler, register operations, wait for shutdown |
| `terminate()` | Signal worker to stop, trigger graceful shutdown |
| `add_operation(func, interval)` | Register a function to run every `interval` seconds |
| `is_healthy()` | Returns `True` if worker hasn't been stopped |
| `join()` | Gracefully terminate and wait for completion |

### Startup Checks

Workers skip startup if:
- `SETUP_COMPLETE` is `False` - Product not yet configured
- `REGISTRY_STATE` is `readonly` - Registry in read-only mode

See: `workers/worker.py:144-156`

## Queue Worker

`QueueWorker` extends `Worker` to process jobs from a database-backed queue.

See: `workers/queueworker.py:50-188`

### Constructor Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `queue` | required | `WorkQueue` instance to consume from |
| `poll_period_seconds` | 30 | How often to check for new jobs |
| `reservation_seconds` | 300 | How long a job is reserved before timeout |
| `watchdog_period_seconds` | 60 | Interval for health check callback |
| `retry_after_seconds` | 300 | Delay before retrying failed jobs |

### Key Methods

| Method | Purpose |
|--------|---------|
| `process_queue_item(job_details)` | **Abstract** - Implement to handle job processing |
| `watchdog()` | Override for periodic health checks |
| `extend_processing(seconds, data)` | Extend reservation time for long-running jobs |
| `mark_current_complete()` | Mark current job as successfully completed |
| `mark_current_incomplete(restore_retry)` | Return job to queue for retry |

### Processing Loop

```python
def poll_queue(self):
    self.current_queue_item = self._queue.get(processing_time=self._reservation_seconds)
    while self.current_queue_item:
        job_details = json.loads(self.current_queue_item.body)
        try:
            self.process_queue_item(job_details)
            self.mark_current_complete()
        except JobException:
            self.mark_current_incomplete(restore_retry=False)
        except WorkerSleepException:
            self.mark_current_incomplete(restore_retry=True)
        except WorkerUnhealthyException:
            self.mark_current_incomplete(restore_retry=True)
            self._stop.set()
```

## Exception Handling

Queue workers use exceptions to control job retry behavior.

See: `workers/queueworker.py:15-47`

| Exception | Behavior | Use Case |
|-----------|----------|----------|
| `JobException` | Job permanently fails, no retry | Malformed job data, unrecoverable error |
| `WorkerUnhealthyException` | Job retried, worker stops accepting new jobs | External dependency failure |
| `WorkerSleepException` | Job retried, worker pauses briefly | Another worker handling the work |

Example:
```python
def process_queue_item(self, job_details):
    try:
        with GlobalLock("LARGE_GARBAGE_COLLECTION", lock_ttl=TIMEOUT):
            self._perform_gc(job_details)
    except LockNotAcquiredException:
        raise WorkerSleepException  # Another worker has the lock
```

See: `workers/repositorygcworker.py:25-33`

## Queue System

Quay uses a database-backed queue implemented via the `QueueItem` model.

See: `data/queue.py:45-428`

### WorkQueue Class

| Method | Purpose |
|--------|---------|
| `put(name_list, message, available_after, retries)` | Enqueue a new job |
| `get(processing_time)` | Claim an available job |
| `complete(item)` | Remove completed job from queue |
| `incomplete(item, retry_after, restore_retry)` | Return job for retry |
| `extend_processing(item, seconds, data)` | Extend processing time |
| `cancel(item_id)` | Delete a job from queue |

### Enqueueing Jobs

```python
from data.queue import WorkQueue

queue = WorkQueue("repositorygc", transaction_factory, has_namespace=True)
queue.put(
    ["namespace", "repository"],      # Canonical name path
    json.dumps({"marker_id": 123}),   # Job body (JSON string)
    available_after=0,                # Seconds until available
    retries_remaining=5               # Retry attempts
)
```

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `quay_queue_item_puts_total` | Counter | Items added to queue |
| `quay_queue_item_gets_total` | Counter | Queue get() calls (with availability label) |
| `quay_queue_items_locked` | Gauge | Items currently being processed |
| `quay_queue_items_available` | Gauge | Items available for processing |
| `quay_queue_items_available_unlocked` | Gauge | Available items not currently locked |

See: `data/queue.py:10-38`

## Queue Definitions

Queues are instantiated in `app.py` using the `WorkQueue` class.

See: `app.py:259-310`

| Queue Variable | Config Key | Namespaced |
|----------------|------------|------------|
| `chunk_cleanup_queue` | `CHUNK_CLEANUP_QUEUE_NAME` | No |
| `image_replication_queue` | `REPLICATION_QUEUE_NAME` | No |
| `dockerfile_build_queue` | `DOCKERFILE_BUILD_QUEUE_NAME` | Yes |
| `notification_queue` | `NOTIFICATION_QUEUE_NAME` | Yes |
| `secscan_notification_queue` | `SECSCAN_V4_NOTIFICATION_QUEUE_NAME` | No |
| `export_action_logs_queue` | `EXPORT_ACTION_LOGS_QUEUE_NAME` | Yes |
| `repository_gc_queue` | `REPOSITORY_GC_QUEUE_NAME` | Yes |
| `namespace_gc_queue` | `NAMESPACE_GC_QUEUE_NAME` | No |
| `proxy_cache_blob_queue` | `PROXY_CACHE_BLOB_QUEUE_NAME` | Yes |

**Namespaced queues** have their items deleted when a namespace is marked for deletion.

## Configuration

| Config Key | Default | Purpose |
|------------|---------|---------|
| `QUEUE_WORKER_METRICS_REFRESH_SECONDS` | 300 | Interval for updating queue Prometheus metrics |
| `STAGGER_WORKERS` | True | Randomize worker start times to prevent thundering herd |
| `TEAM_SYNC_WORKER_FREQUENCY` | 60 | Team sync interval in seconds |

See: `config.py:278-631`

## Creating a New Worker

### Queue Worker Example

Based on: `workers/repositorygcworker.py`

```python
import logging
from app import app, my_queue
from workers.queueworker import QueueWorker, JobException
from workers.gunicorn_worker import GunicornWorker
import features

logger = logging.getLogger(__name__)

POLL_PERIOD_SECONDS = 60
RESERVATION_SECONDS = 300

class MyWorker(QueueWorker):
    """Worker which processes my queue items."""

    def process_queue_item(self, job_details):
        item_id = job_details.get("item_id")
        if not item_id:
            raise JobException("Missing item_id")

        # Process the job
        process_item(item_id)

def create_gunicorn_worker():
    """Factory for running as gunicorn worker (hot reload support)."""
    worker = MyWorker(
        my_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    return GunicornWorker(__name__, app, worker, features.MY_FEATURE)

if __name__ == "__main__":
    if not features.MY_FEATURE:
        logger.info("Feature disabled; skipping")
        while True:
            time.sleep(100000)

    worker = MyWorker(
        my_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker.start()
```

### Periodic Worker Example

```python
from workers.worker import Worker

class MyPeriodicWorker(Worker):
    def __init__(self):
        super().__init__()
        self.add_operation(self.do_work, 60)  # Run every 60 seconds

    def do_work(self):
        # Perform periodic task
        cleanup_old_records()

if __name__ == "__main__":
    worker = MyPeriodicWorker()
    worker.start()
```

## Running Workers

### Standalone Execution

```bash
# Run a worker directly
python -m workers.repositorygcworker

# With environment variables
QUAY_CONFIG=/conf/stack python -m workers.repositorygcworker
```

### Via Gunicorn (Local Development)

Workers that implement `create_gunicorn_worker()` can be run with gunicorn for hot reload:

```bash
gunicorn -c conf/gunicorn_worker.py workers.repositorygcworker:create_gunicorn_worker
```

See: `workers/gunicorn_worker.py`

## Utilities

### Exponential Backoff Decorator

Automatically retry operations with exponential backoff on failure.

See: `workers/worker.py:27-56`

```python
from workers.worker import with_exponential_backoff

@with_exponential_backoff(backoff_multiplier=10, max_backoff=3600, max_retries=10)
def unreliable_operation():
    # Operation that may fail temporarily
    external_api_call()
```

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `backoff_multiplier` | 10 | Base multiplier for backoff calculation |
| `max_backoff` | 3600 | Maximum wait time in seconds |
| `max_retries` | 10 | Maximum retry attempts before re-raising |

Wait time formula: `min(2^attempts * backoff_multiplier, max_backoff)`

## Testing

Worker tests are located alongside other unit tests.

```bash
# Run worker-related tests
TEST=true PYTHONPATH="." pytest workers/ -v
TEST=true PYTHONPATH="." pytest test/workers/ -v
```

For testing patterns, see: `docs/agents/testing.md`
