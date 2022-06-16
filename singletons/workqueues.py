from data.queue import WorkQueue
from singletons.config import app_config

tf = app_config["DB_TRANSACTION_FACTORY"]

chunk_cleanup_queue = WorkQueue(app_config["CHUNK_CLEANUP_QUEUE_NAME"], tf)
image_replication_queue = WorkQueue(app_config["REPLICATION_QUEUE_NAME"], tf, has_namespace=False)
dockerfile_build_queue = WorkQueue(
    app_config["DOCKERFILE_BUILD_QUEUE_NAME"], tf, has_namespace=True
)
notification_queue = WorkQueue(app_config["NOTIFICATION_QUEUE_NAME"], tf, has_namespace=True)
secscan_notification_queue = WorkQueue(
    app_config["SECSCAN_V4_NOTIFICATION_QUEUE_NAME"], tf, has_namespace=False
)
export_action_logs_queue = WorkQueue(
    app_config["EXPORT_ACTION_LOGS_QUEUE_NAME"], tf, has_namespace=True
)

repository_gc_queue = WorkQueue(app_config["REPOSITORY_GC_QUEUE_NAME"], tf, has_namespace=True)

# Note: We set `has_namespace` to `False` here, as we explicitly want this queue to not be emptied
# when a namespace is marked for deletion.
namespace_gc_queue = WorkQueue(app_config["NAMESPACE_GC_QUEUE_NAME"], tf, has_namespace=False)

all_queues = [
    image_replication_queue,
    dockerfile_build_queue,
    notification_queue,
    chunk_cleanup_queue,
    repository_gc_queue,
    namespace_gc_queue,
]
