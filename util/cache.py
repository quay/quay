from functools import wraps

from flask_restful.utils import unpack


def cache_control(max_age=55):
    def wrap(f):
        @wraps(f)
        def add_max_age(*args, **kwargs):
            response = f(*args, **kwargs)
            response.headers["Cache-Control"] = "max-age=%d" % max_age
            return response

        return add_max_age

    return wrap


def cache_control_flask_restful(max_age=55):
    def wrap(f):
        @wraps(f)
        def add_max_age(*args, **kwargs):
            response = f(*args, **kwargs)
            body, status_code, headers = unpack(response)
            headers["Cache-Control"] = "max-age=%d" % max_age
            return body, status_code, headers

        return add_max_age

    return wrap


def no_cache(f):
    @wraps(f)
    def add_no_cache(*args, **kwargs):
        response = f(*args, **kwargs)
        if response is not None:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    return add_no_cache
