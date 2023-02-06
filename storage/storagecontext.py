from util.ipresolver import NoopIPResolver


class StorageContext(object):
    def __init__(self, location, chunk_cleanup_queue, config_provider, ip_resolver):
        self.location = location
        self.chunk_cleanup_queue = chunk_cleanup_queue
        self.config_provider = config_provider
        self.ip_resolver = ip_resolver or NoopIPResolver()
