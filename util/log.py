import os
from _init import CONF_DIR


def logfile_path(jsonfmt=False, debug=False):
    """
    Returns the a logfileconf path following this rules:

      - conf/logging_debug_json.conf # jsonfmt=true,  debug=true
      - conf/logging_json.conf       # jsonfmt=true,  debug=false
      - conf/logging_debug.conf      # jsonfmt=false, debug=true
      - conf/logging.conf            # jsonfmt=false, debug=false
    Can be parametrized via envvars: JSONLOG=true, DEBUGLOG=true
    """
    _json = ""
    _debug = ""

    if jsonfmt or os.getenv("JSONLOG", "false").lower() == "true":
        _json = "_json"

    if debug or os.getenv("DEBUGLOG", "false").lower() == "true":
        _debug = "_debug"

    return os.path.join(CONF_DIR, "logging%s%s.conf" % (_debug, _json))


def filter_logs(values, filtered_fields):
    """
    Takes a dict and a list of keys to filter.
    eg:
     with filtered_fields:
        [{'key': ['k1', k2'], 'fn': lambda x: 'filtered'}]
     and values:
       {'k1': {'k2': 'some-secret'}, 'k3': 'some-value'}
    the returned dict is:
      {'k1': {k2: 'filtered'}, 'k3': 'some-value'}
    """
    for field in filtered_fields:
        cdict = values

        for key in field["key"][:-1]:
            if key in cdict:
                cdict = cdict[key]

        last_key = field["key"][-1]

        if last_key in cdict and cdict[last_key]:
            cdict[last_key] = field["fn"](cdict[last_key])
