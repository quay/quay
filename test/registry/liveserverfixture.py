import inspect
import json
import multiprocessing
import socket
import socketserver
import time

from contextlib import contextmanager
from urllib.parse import urlparse, urljoin

import pytest
import requests

from flask import request
from flask.blueprints import Blueprint


class liveFlaskServer(object):
    """
    Helper class for spawning a live Flask server for testing.

    Based on https://github.com/jarus/flask-testing/blob/master/flask_testing/utils.py#L421
    """

    def __init__(self, app, port_value):
        self.app = app
        self._port_value = port_value
        self._process = None

    def get_server_url(self):
        """
        Return the url of the test server.
        """
        return "http://localhost:%s" % self._port_value.value

    def terminate_live_server(self):
        if self._process:
            self._process.terminate()

    def spawn_live_server(self):
        self._process = None
        port_value = self._port_value

        def worker(app, port):
            # Based on solution: http://stackoverflow.com/a/27598916
            # Monkey-patch the server_bind so we can determine the port bound by Flask.
            # This handles the case where the port specified is `0`, which means that
            # the OS chooses the port. This is the only known way (currently) of getting
            # the port out of Flask once we call `run`.
            original_socket_bind = socketserver.TCPServer.server_bind

            def socket_bind_wrapper(self):
                ret = original_socket_bind(self)

                # Get the port and save it into the port_value, so the parent process
                # can read it.
                (_, port) = self.socket.getsockname()
                port_value.value = port
                socketserver.TCPServer.server_bind = original_socket_bind
                return ret

            socketserver.TCPServer.server_bind = socket_bind_wrapper
            app.run(port=port, use_reloader=False)

        retry_count = self.app.config.get("LIVESERVER_RETRY_COUNT", 3)
        started = False
        for _ in range(0, retry_count):
            if started:
                break

            self._process = multiprocessing.Process(target=worker, args=(self.app, 0))
            self._process.start()

            # We must wait for the server to start listening, but give up
            # after a specified maximum timeout
            timeout = self.app.config.get("LIVESERVER_TIMEOUT", 10)
            start_time = time.time()

            while True:
                time.sleep(0.1)

                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    break

                if self._can_connect():
                    self.app.config["SERVER_HOSTNAME"] = "localhost:%s" % self._port_value.value
                    started = True
                    break

        if not started:
            raise RuntimeError("Failed to start the server after %d retries. " % retry_count)

    def _can_connect(self):
        host, port = self._get_server_address()
        if port == 0:
            # Port specified by the user was 0, and the OS has not yet assigned
            # the proper port.
            return False

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
        except socket.error:
            success = False
        else:
            success = True
        finally:
            sock.close()

        return success

    def _get_server_address(self):
        """
        Gets the server address used to test the connection with a socket.

        Respects both the LIVESERVER_PORT config value and overriding get_server_url()
        """
        parts = urlparse(self.get_server_url())

        host = parts.hostname
        port = parts.port

        if port is None:
            if parts.scheme == "http":
                port = 80
            elif parts.scheme == "https":
                port = 443
            else:
                raise RuntimeError("Unsupported server url scheme: %s" % parts.scheme)

        return host, port


class LiveFixtureServerSession(object):
    """
    Helper class for calling the live server via a single requests Session.
    """

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def _get_url(self, url):
        return urljoin(self.base_url, url)

    def get(self, url, **kwargs):
        return self.session.get(self._get_url(url), **kwargs)

    def post(self, url, **kwargs):
        return self.session.post(self._get_url(url), **kwargs)

    def put(self, url, **kwargs):
        return self.session.put(self._get_url(url), **kwargs)

    def delete(self, url, **kwargs):
        return self.session.delete(self._get_url(url), **kwargs)

    def request(self, method, url, **kwargs):
        return self.session.request(method, self._get_url(url), **kwargs)


class LiveFixtureServer(object):
    """
    Helper for interacting with a live server.
    """

    def __init__(self, url):
        self.url = url

    @contextmanager
    def session(self):
        """
        Yields a session for speaking to the live server.
        """
        yield LiveFixtureServerSession(self.url)

    def new_session(self):
        """
        Returns a new session for speaking to the live server.
        """
        return LiveFixtureServerSession(self.url)


@pytest.fixture(scope="function")
def liveserver(liveserver_app):
    """
    Runs a live Flask server for the app for the duration of the test.

    Based on https://github.com/jarus/flask-testing/blob/master/flask_testing/utils.py#L421
    """
    context = liveserver_app.test_request_context()
    context.push()

    port = multiprocessing.Value("i", 0)
    live_server = liveFlaskServer(liveserver_app, port)

    try:
        live_server.spawn_live_server()
        yield LiveFixtureServer(live_server.get_server_url())
    finally:
        context.pop()
        live_server.terminate_live_server()


@pytest.fixture(scope="function")
def liveserver_session(liveserver, liveserver_app):
    """
    Fixtures which instantiates a liveserver and returns a single session for interacting with that
    server.
    """
    return LiveFixtureServerSession(liveserver.url)


class LiveServerExecutor(object):
    """
    Helper class which can be used to register functions to be executed in the same process as the
    live server. This is necessary because the live server runs in a different process and,
    therefore, in order to execute state changes outside of the server's normal flows (i.e. via
    code), it must be executed.

    *in-process* via an HTTP call. The LiveServerExecutor class abstracts away
    all the setup for this process.

    Usage:
      def _perform_operation(first_param, second_param):
        ... do some operation in the app ...
        return 'some value'

      @pytest.fixture(scope="session")
      def my_server_executor():
        executor = LiveServerExecutor()
        executor.register('performoperation', _perform_operation)
        return executor

      @pytest.fixture()
      def liveserver_app(app, my_server_executor):
        ... other app setup here ...
        my_server_executor.apply_blueprint_to_app(app)
        return app

      def test_mytest(liveserver, my_server_executor):
        # Invokes 'performoperation' in the liveserver's process.
        my_server_executor.on(liveserver).performoperation('first', 'second')
    """

    def __init__(self):
        self.funcs = {}

    def register(self, fn_name, fn):
        """
        Registers the given function under the given name.
        """
        self.funcs[fn_name] = fn

    def apply_blueprint_to_app(self, app):
        """
        Applies a blueprint to the app, to support invocation from this executor.
        """
        testbp = Blueprint("testbp", __name__)

        def build_invoker(fn_name, fn):
            path = "/" + fn_name

            @testbp.route(path, methods=["POST"], endpoint=fn_name)
            def _(**kwargs):
                arg_values = request.get_json()["args"]
                return fn(*arg_values)

        for fn_name, fn in self.funcs.items():
            build_invoker(fn_name, fn)

        app.register_blueprint(testbp, url_prefix="/__test")

    def on(self, server):
        """
        Returns an invoker for the given live server.
        """
        return liveServerExecutorInvoker(self.funcs, server)

    def on_session(self, server_session):
        """
        Returns an invoker for the given live server session.
        """
        return liveServerExecutorInvoker(self.funcs, server_session)


class liveServerExecutorInvoker(object):
    def __init__(self, funcs, server_or_session):
        self._funcs = funcs
        self._server_or_session = server_or_session

    def __getattribute__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        if name not in self._funcs:
            raise AttributeError("Unknown function: %s" % name)

        def invoker(*args):
            path = "/__test/%s" % name
            headers = {"Content-Type": "application/json"}

            if isinstance(self._server_or_session, LiveFixtureServerSession):
                return self._server_or_session.post(
                    path, data=json.dumps({"args": args}), headers=headers
                )
            else:
                with self._server_or_session.session() as session:
                    return session.post(path, data=json.dumps({"args": args}), headers=headers)

        return invoker
