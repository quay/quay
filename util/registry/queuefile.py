class QueueFile(object):
    """ Class which implements a file-like interface and reads QueueResult's from a blocking
      multiprocessing queue.
  """

    def __init__(self, queue, name=None):
        self._queue = queue
        self._closed = False
        self._done = False
        self._buffer = ""
        self._total_size = 0
        self._name = name
        self.raised_exception = False
        self._exception_handlers = []

    def add_exception_handler(self, handler):
        self._exception_handlers.append(handler)

    def read(self, size=-1):
        # If the queuefile was closed or we have finished, send back any remaining data.
        if self._closed or self._done:
            if size == -1:
                buf = self._buffer
                self._buffer = ""
                return buf

            buf = self._buffer[0:size]
            self._buffer = self._buffer[size:]
            return buf

        # Loop until we reach the requested data size (or forever if all data was requested).
        while (len(self._buffer) < size) or (size == -1):
            result = self._queue.get(block=True)

            # Check for any exceptions raised by the queue process.
            if result.exception is not None:
                self._closed = True
                self.raised_exception = True

                # Fire off the exception to any registered handlers. If no handlers were registered,
                # then raise the exception locally.
                handled = False
                for handler in self._exception_handlers:
                    handler(result.exception)
                    handled = True

                if handled:
                    return ""
                else:
                    raise result.exception

            # Check for no further data. If the QueueProcess has finished producing data, then break
            # out of the loop to return the data already acquired.
            if result.data is None:
                self._done = True
                break

            # Add the data to the buffer.
            self._buffer += result.data
            self._total_size += len(result.data)

        # Return the requested slice of the buffer.
        if size == -1:
            buf = self._buffer
            self._buffer = ""
            return buf

        buf = self._buffer[0:size]
        self._buffer = self._buffer[size:]
        return buf

    def flush(self):
        # Purposefully not implemented.
        pass

    def close(self):
        self._closed = True
