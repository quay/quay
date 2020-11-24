import logging
import grpc
import json

from concurrent import futures
from datetime import timedelta
from threading import Event

from flask import Flask

from app import app
from buildman.buildmanagerservicer import BuildManagerServicer
from buildman.buildman_pb import buildman_pb2, buildman_pb2_grpc

from buildman.jobutil.buildjob import BuildJob, BuildJobLoadException
from data import database, model


logger = logging.getLogger(__name__)


DEFAULT_GRPC_SERVER_PORT = 50051
DEFAULT_GRPC_SERVER_WORKER_COUNT = 10


class BuilderServer(object):
    """
    Server which handles starting the gRPC gateway, along with initializing the build manager
    and starting its reconciliation loop.
    """

    def __init__(
        self,
        registry_hostname,
        manager_hostname,
        queue,
        build_logs,
        user_files,
        lifecycle_manager_klass,
        lifecycle_manager_config,
        instance_keys,
    ):
        self._registry_hostname = registry_hostname
        self._manager_hostname = manager_hostname
        self._queue = queue
        self._build_logs = build_logs
        self._user_files = user_files
        self._instance_keys = instance_keys
        self._lifecycle_manager = lifecycle_manager_klass(
            self._registry_hostname,
            self._manager_hostname,
            self._queue,
            self._build_logs,
            self._user_files,
            self._instance_keys,
        )
        self._lifecycle_manager_config = lifecycle_manager_config

        self._shutdown_event = Event()

    def run(self, host, controller_port):
        logger.debug("Initializing the lifecycle manager")
        self._lifecycle_manager.initialize(self._lifecycle_manager_config)

        logger.debug("Initializing the gRPC server")
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=DEFAULT_GRPC_SERVER_WORKER_COUNT))
        buildman_pb2_grpc.add_BuildManagerServicer_to_server(
            BuildManagerServicer(self._lifecycle_manager), server
        )
        server.add_insecure_port("[::]:"+str(DEFAULT_GRPC_SERVER_PORT))

        logger.debug("Starting the gRPC server...")
        server.start()

        logger.debug("Starting the build manager...")
        try:
            self._lifecycle_manager._work_checker()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error("Build manager work checker exception: %s", e)
            raise

        server.stop(grace=5)
