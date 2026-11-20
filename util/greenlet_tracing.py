import weakref
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
greenlet_lifetime = Histogram(
    "quay_greenlet_lifetime_seconds",
    "wall-clock lifetime of a greenlet from creation to death",
    buckets=(0.1, 0.5, 1, 5, 15, 30, 60, 120, 300, 1200, float("inf")),
)

_latest_switch = None
_tracked_greenlets = weakref.WeakKeyDictionary()


def enable_tracing():
    settrace(greenlet_callback)


def greenlet_callback(event, args):
    """
    Trace callback invoked on every greenlet switch or throw.

    Every switch is a pair: origin -> target.
    - origin: the greenlet that was running and is now yielding or dying
    - target: the greenlet that is about to start running
    - hub: gevent's event loop scheduler — always on one side of every switch

    Example lifecycle of a pull request:
      hub -> greenlet A       (new request arrives, hub dispatches)
      greenlet A -> hub       (A yields for DB I/O)
      hub -> greenlet A       (DB ready, hub wakes A)
      greenlet A -> hub       (A sends response, A.dead=True — slot freed)
    """
    if event in ("switch", "throw"):
        origin, target = args

        hub = get_hub()

        # First time seeing this greenlet — treat as "created".
        # e.g. hub -> new greenlet A: A is not in _tracked_greenlets yet.
        if target is not hub and target not in _tracked_greenlets:
            _tracked_greenlets[target] = time()

        # Greenlet finished execution — treat as "destroyed".
        # e.g. greenlet A -> hub with A.dead=True: A sent its response
        # and will never run again — free the slot.
        if origin is not hub and origin.dead:
            start = _tracked_greenlets.pop(origin, None)
            if start is not None:
                greenlet_lifetime.observe(time() - start)

        # Set gauge from dict size on every switch — avoids drift from
        # greenlets that are GC'd without dying or created before tracing.
        greenlets_active.set(len(_tracked_greenlets))

        # Hub switches are bookkeeping — the hub dispatches to user
        # greenlets but is not itself a request-serving greenlet.
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
