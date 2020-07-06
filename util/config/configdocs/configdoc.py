"""
Generates html documentation from JSON Schema.
"""


import json
from collections import OrderedDict

import docsmodel
import html_output

from util.config.schema import CONFIG_SCHEMA


def make_custom_sort(orders):
    """
    Sort in a specified order any dictionary nested in a complex structure.
    """

    orders = [{k: -i for (i, k) in enumerate(reversed(order), 1)} for order in orders]

    def process(stuff):
        if isinstance(stuff, dict):
            l = [(k, process(v)) for (k, v) in stuff.items()]
            keys = set(stuff)
            for order in orders:
                if keys.issubset(order) or keys.issuperset(order):
                    return OrderedDict(sorted(l, key=lambda x: order.get(x[0], 0)))
            return OrderedDict(sorted(l))
        if isinstance(stuff, list):
            return [process(x) for x in stuff]
        return stuff

    return process


SCHEMA_HTML_FILE = "schema.html"

schema = json.dumps(CONFIG_SCHEMA, sort_keys=True)
schema = json.loads(schema, object_pairs_hook=OrderedDict)

req = sorted(schema["required"])
custom_sort = make_custom_sort([req])
schema = custom_sort(schema)

parsed_items = docsmodel.DocsModel().parse(schema)[1:]
output = html_output.HtmlOutput().generate_output(parsed_items)

with open(SCHEMA_HTML_FILE, "wt") as f:
    f.write(output)
