from singletons.app import _app
from singletons.config import config_provider
from singletons.instance_keys import instance_keys
from singletons.ip_resolver import ip_resolver
from singletons.workqueues import chunk_cleanup_queue
from storage import Storage

storage = Storage(_app, chunk_cleanup_queue, instance_keys, config_provider, ip_resolver)
