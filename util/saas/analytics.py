import json
import logging

from queue import Queue
from threading import Thread
from mixpanel import BufferedConsumer, Mixpanel


logger = logging.getLogger(__name__)


class MixpanelQueuingConsumer(object):
    def __init__(self, request_queue):
        self._mp_queue = request_queue

    def send(self, endpoint, json_message):
        logger.debug("Queuing mixpanel request.")
        self._mp_queue.put(json.dumps([endpoint, json_message]))


class SendToMixpanel(Thread):
    def __init__(self, request_queue):
        Thread.__init__(self)
        self.daemon = True

        self._mp_queue = request_queue
        self._consumer = BufferedConsumer()

    def run(self):
        logger.debug("Starting mixpanel sender process.")
        while True:
            mp_request = self._mp_queue.get()
            logger.debug("Got queued mixpanel request.")
            try:
                self._consumer.send(*json.loads(mp_request))
            except:
                logger.exception("Failed to send Mixpanel request.")


class _FakeMixpanel(object):
    def track(*args, **kwargs):
        pass


class Analytics(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        analytics_type = app.config.get("ANALYTICS_TYPE", "FakeAnalytics")

        if analytics_type == "Mixpanel":
            mixpanel_key = app.config.get("MIXPANEL_KEY", "")
            logger.debug("Initializing mixpanel with key: %s", app.config["MIXPANEL_KEY"])

            request_queue = Queue()
            analytics = Mixpanel(mixpanel_key, MixpanelQueuingConsumer(request_queue))
            SendToMixpanel(request_queue).start()

        else:
            analytics = _FakeMixpanel()

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["analytics"] = analytics
        return analytics

    def __getattr__(self, name):
        return getattr(self.state, name, None)
