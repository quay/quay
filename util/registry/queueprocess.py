from multiprocessing import Process, Queue
from collections import namedtuple

import logging
import multiprocessing
import time
import sys
import traceback


logger = multiprocessing.log_to_stderr()
logger.setLevel(logging.INFO)


class QueueProcess(object):
    """
    Helper class which invokes a worker in a process to produce data for one (or more) queues.
    """

    def __init__(self, get_producer, chunk_size, max_size, args, finished=None):
        self._get_producer = get_producer
        self._queues = []
        self._chunk_size = chunk_size
        self._max_size = max_size
        self._args = args or []
        self._finished = finished

    def create_queue(self):
        """
        Adds a multiprocessing queue to the list of queues.

        Any queues added will have the data produced appended.
        """
        queue = Queue(self._max_size // self._chunk_size)
        self._queues.append(queue)
        return queue

    @staticmethod
    def run_process(target, args, finished=None):
        def _target(tar, arg, fin):
            try:
                tar(*args)
            finally:
                if fin:
                    fin()

        Process(target=_target, args=(target, args, finished)).start()

    def run(self):
        # Important! gipc is used here because normal multiprocessing does not work
        # correctly with gevent when we sleep.
        args = (self._get_producer, self._queues, self._chunk_size, self._args)
        QueueProcess.run_process(_run, args, finished=self._finished)


QueueResult = namedtuple("QueueResult", ["data", "exception"])


def _run(get_producer, queues, chunk_size, args):
    producer = get_producer(*args)
    while True:
        try:
            result = QueueResult(producer(chunk_size) or None, None)
        except Exception as ex:
            message = "%s\n%s" % (str(ex), "".join(traceback.format_exception(*sys.exc_info())))
            result = QueueResult(None, Exception(message))

        for queue in queues:
            try:
                queue.put(result, block=True)
            except Exception as ex:
                logger.exception("Exception writing to queue.")
                return

        # Terminate the producer loop if the data produced is empty or an exception occurred.
        if result.data is None or result.exception is not None:
            break

        # Important! This allows the thread that writes the queue data to the pipe
        # to do so. Otherwise, this hangs.
        time.sleep(0)
