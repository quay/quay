from time import time

from gevent.hub import get_hub
from greenlet import settrace
from prometheus_client import Counter, Gauge, Histogram

greenlet_switch = Counter("greenlet_switch_total", "number of greenlet context switches")
greenlet_throw = Counter("greenlet_throw_total", "number of greenlet throws")
greenlet_duration = Histogram(
    "greenlet_duration_seconds",
    "seconds in which a particular greenlet is executing",
)
greenlets_active = Gauge(
    "quay_greenlets_active",
    "number of greenlets currently active (excludes the hub)",
)

_latest_switch = None
_tracked_greenlets = set()


def enable_tracing():
    settrace(greenlet_callback)


def greenlet_callback(event, args):
    """
    This is a callback that is executed greenlet on all events.
    """
    if event in ("switch", "throw"):
        origin, target = args

        hub = get_hub()

        if target is not hub and target not in _tracked_greenlets:
            _tracked_greenlets.add(target)
            greenlets_active.inc()

        if origin is not hub and origin.dead:
            _tracked_greenlets.discard(origin)
            greenlets_active.dec()

        if origin is hub:
            if event == "switch":
                switch_callback(args)
            elif event == "throw":
                throw_callback(args)
            return

        if event == "switch":
            switch_callback(args)
            return
        if event == "throw":
            throw_callback(args)
            return


def switch_callback(_args):
    """
    This is a callback that is executed specifically on greenlet switches.
    """
    global _latest_switch
    greenlet_switch.inc()

    if _latest_switch is None:
        _latest_switch = time()
        return

    now = time()
    greenlet_duration.observe(now - _latest_switch)
    _latest_switch = now


def throw_callback(_args):
    """
    This is a callback that is executed on execeptions from origin to target.

    This callback is running in the context of the target greenlet and any exceptions will replace
    the original, as if target.throw() was used replacing the exception.
    """
    greenlet_throw.inc()
