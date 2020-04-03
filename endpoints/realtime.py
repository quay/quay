import logging
import json

from flask import request, Blueprint, abort, Response
from flask_login import current_user

from app import userevents
from auth.decorators import require_session_login
from data.userevent import CannotReadUserEventsException


logger = logging.getLogger(__name__)


realtime = Blueprint("realtime", __name__)


@realtime.route("/user/test")
@require_session_login
def user_test():
    evt = userevents.get_event(current_user.db_user().username)
    evt.publish_event_data("test", {"foo": 2})
    return "OK"


@realtime.route("/user/subscribe")
@require_session_login
def user_subscribe():
    def wrapper(listener):
        logger.debug("Beginning streaming of user events")
        try:
            yield "data: %s\n\n" % json.dumps({})

            for event_id, data in listener.event_stream():
                message = {"event": event_id, "data": data}
                json_string = json.dumps(message)
                yield "data: %s\n\n" % json_string
        finally:
            logger.debug("Closing listener due to exception")
            listener.stop()

    events = request.args.get("events", "").split(",")
    if not events:
        abort(404)

    try:
        listener = userevents.get_listener(current_user.db_user().username, events)
    except CannotReadUserEventsException:
        abort(504)

    def on_close():
        logger.debug("Closing listener due to response close")
        listener.stop()

    r = Response(wrapper(listener), mimetype="text/event-stream")
    r.call_on_close(on_close)
    return r
