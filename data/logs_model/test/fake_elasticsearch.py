import json
import uuid
import fnmatch

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

import dateutil.parser

from httmock import urlmatch, HTTMock

FAKE_ES_HOST = "fakees"

EMPTY_RESULT = {
    "hits": {"hits": [], "total": 0},
    "_shards": {"successful": 1, "total": 1},
}


def parse_query(query):
    if not query:
        return {}

    return {s.split("=")[0]: s.split("=")[1] for s in query.split("&")}


@contextmanager
def fake_elasticsearch(allow_wildcard=True):
    templates = {}
    docs = defaultdict(list)
    scrolls = {}
    id_counter = [1]

    def transform(value, field_name):
        # TODO: implement this using a real index template if we ever need more than a few
        # fields here.
        if field_name == "datetime":
            if isinstance(value, int):
                return datetime.utcfromtimestamp(value // 1000)

            parsed = dateutil.parser.parse(value)
            return parsed

        return value

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/_template/(.+)", method="GET")
    def get_template(url, request):
        template_name = url[len("/_template/") :]
        if template_name in templates:
            return {"status_code": 200}

        return {"status_code": 404}

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/_template/(.+)", method="PUT")
    def put_template(url, request):
        template_name = url[len("/_template/") :]
        templates[template_name] = True
        return {"status_code": 201}

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/([^/]+)/_doc", method="POST")
    def post_doc(url, request):
        index_name, _ = url.path[1:].split("/")
        item = json.loads(request.body)
        item["_id"] = item["random_id"]
        id_counter[0] += 1
        docs[index_name].append(item)
        return {
            "status_code": 204,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps(
                {
                    "result": "created",
                }
            ),
        }

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/([^/]+)$", method="DELETE")
    def index_delete(url, request):
        index_name_or_pattern = url.path[1:]
        to_delete = []
        for index_name in list(docs.keys()):
            if not fnmatch.fnmatch(index_name, index_name_or_pattern):
                continue

            to_delete.append(index_name)

        for index in to_delete:
            docs.pop(index)

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": {"acknowledged": True},
        }

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/([^/]+)$", method="GET")
    def index_lookup(url, request):
        index_name_or_pattern = url.path[1:]
        found = {}
        for index_name in list(docs.keys()):
            if not fnmatch.fnmatch(index_name, index_name_or_pattern):
                continue

            found[index_name] = {}

        if not found:
            return {
                "status_code": 404,
            }

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps(found),
        }

    def _match_query(index_name_or_pattern, query):
        found = []
        found_index = False

        for index_name in list(docs.keys()):
            if not allow_wildcard and index_name_or_pattern.find("*") >= 0:
                break

            if not fnmatch.fnmatch(index_name, index_name_or_pattern):
                continue

            found_index = True

            def _is_match(doc, current_query):
                if current_query is None:
                    return True

                for filter_type, filter_params in current_query.items():
                    for field_name, filter_props in filter_params.items():
                        if filter_type == "range":
                            lt = transform(filter_props["lt"], field_name)
                            gte = transform(filter_props["gte"], field_name)
                            doc_value = transform(doc[field_name], field_name)
                            if not (doc_value < lt and doc_value >= gte):
                                return False
                        elif filter_type == "term":
                            doc_value = transform(doc[field_name], field_name)
                            return doc_value == filter_props
                        elif filter_type == "terms":
                            doc_value = transform(doc[field_name], field_name)
                            return doc_value in filter_props
                        elif filter_type == "bool":
                            assert not "should" in filter_params, "should is unsupported"

                            must = filter_params.get("must")
                            must_not = filter_params.get("must_not")
                            filter_bool = filter_params.get("filter")

                            if must:
                                for check in must:
                                    if not _is_match(doc, check):
                                        return False

                            if must_not:
                                for check in must_not:
                                    if _is_match(doc, check):
                                        return False

                            if filter_bool:
                                for check in filter_bool:
                                    if not _is_match(doc, check):
                                        return False
                        else:
                            raise Exception("Unimplemented query %s: %s" % (filter_type, query))

                return True

            for doc in docs[index_name]:
                if not _is_match(doc, query):
                    continue

                found.append({"_source": doc, "_index": index_name})

        return found, found_index or (index_name_or_pattern.find("*") >= 0)

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/([^/]+)/_count$", method="GET")
    def count_docs(url, request):
        request = json.loads(request.body)
        index_name_or_pattern, _ = url.path[1:].split("/")

        found, found_index = _match_query(index_name_or_pattern, request["query"])
        if not found_index:
            return {
                "status_code": 404,
            }

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps({"count": len(found)}),
        }

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/_search/scroll$", method="GET")
    def lookup_scroll(url, request):
        request_obj = json.loads(request.body)
        scroll_id = request_obj["scroll_id"]
        if scroll_id in scrolls:
            return {
                "status_code": 200,
                "headers": {
                    "Content-Type": "application/json",
                },
                "content": json.dumps(scrolls[scroll_id]),
            }

        return {
            "status_code": 404,
        }

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/_search/scroll$", method="DELETE")
    def delete_scroll(url, request):
        request = json.loads(request.body)
        for scroll_id in request["scroll_id"]:
            scrolls.pop(scroll_id, None)

        return {
            "status_code": 404,
        }

    @urlmatch(netloc=FAKE_ES_HOST, path=r"/([^/]+)/_search$", method="GET")
    def lookup_docs(url, request):
        query_params = parse_query(url.query)

        request = json.loads(request.body)
        index_name_or_pattern, _ = url.path[1:].split("/")

        # Find matching docs.
        query = request.get("query")
        found, found_index = _match_query(index_name_or_pattern, query)
        if not found_index:
            return {
                "status_code": 404,
            }

        # Sort.
        sort = request.get("sort")
        if sort:
            if sort == ["_doc"] or sort == "_doc":
                found.sort(key=lambda x: x["_source"]["_id"])
            else:

                def get_sort_key(item):
                    source = item["_source"]
                    key = ""
                    for sort_config in sort:
                        for sort_key, direction in sort_config.items():
                            assert direction == "desc"
                            sort_key = sort_key.replace(".keyword", "")
                            key += str(transform(source[sort_key], sort_key))
                            key += "|"
                    return key

                found.sort(key=get_sort_key, reverse=True)

        # Search after.
        search_after = request.get("search_after")
        if search_after:
            sort_fields = []
            for sort_config in sort:
                if isinstance(sort_config, str):
                    sort_fields.append(sort_config)
                    continue

                for sort_key, _ in sort_config.items():
                    sort_key = sort_key.replace(".keyword", "")
                    sort_fields.append(sort_key)

            for index, search_after_value in enumerate(search_after):
                field_name = sort_fields[index]
                value = transform(search_after_value, field_name)
                if field_name == "_doc":
                    found = [f for f in found if transform(f["_source"]["_id"], field_name) > value]
                else:
                    found = [
                        f for f in found if transform(f["_source"][field_name], field_name) < value
                    ]
                if len(found) < 2:
                    break

                if field_name == "_doc":
                    if found[0]["_source"]["_id"] != found[1]["_source"]:
                        break
                else:
                    if found[0]["_source"][field_name] != found[1]["_source"]:
                        break

        # Size.
        size = request.get("size")
        if size:
            found = found[0:size]

        # Aggregation.
        # {u'query':
        #   {u'range':
        #     {u'datetime': {u'lt': u'2019-06-27T15:45:09.768085',
        #                    u'gte': u'2019-06-27T15:35:09.768085'}}},
        #      u'aggs': {
        #         u'by_id': {
        #           u'terms': {u'field': u'kind_id'},
        #           u'aggs': {
        #             u'by_date': {u'date_histogram': {u'field': u'datetime', u'interval': u'day'}}}}},
        #   u'size': 0}
        def _by_field(agg_field_params, results):
            aggregated_by_field = defaultdict(list)

            for agg_means, agg_means_params in agg_field_params.items():
                if agg_means == "terms":
                    field_name = agg_means_params["field"]
                    for result in results:
                        value = result["_source"][field_name]
                        aggregated_by_field[value].append(result)
                elif agg_means == "date_histogram":
                    field_name = agg_means_params["field"]
                    interval = agg_means_params["interval"]
                    for result in results:
                        value = transform(result["_source"][field_name], field_name)
                        aggregated_by_field[getattr(value, interval)].append(result)
                elif agg_means == "aggs":
                    # Skip. Handled below.
                    continue
                else:
                    raise Exception("Unsupported aggregation method: %s" % agg_means)

            # Invoke the aggregation recursively.
            buckets = []
            for field_value, field_results in aggregated_by_field.items():
                aggregated = _aggregate(agg_field_params, field_results)
                if isinstance(aggregated, list):
                    aggregated = {"doc_count": len(aggregated)}

                aggregated["key"] = field_value
                buckets.append(aggregated)

            return {"buckets": buckets}

        def _aggregate(query_config, results):
            agg_params = query_config.get("aggs")
            if not agg_params:
                return results

            by_field_name = {}
            for agg_field_name, agg_field_params in agg_params.items():
                by_field_name[agg_field_name] = _by_field(agg_field_params, results)

            return by_field_name

        final_result = {
            "hits": {
                "hits": found,
                "total": len(found),
            },
            "_shards": {
                "successful": 1,
                "total": 1,
            },
            "aggregations": _aggregate(request, found),
        }

        if query_params.get("scroll"):
            scroll_id = str(uuid.uuid4())
            scrolls[scroll_id] = EMPTY_RESULT
            final_result["_scroll_id"] = scroll_id

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "content": json.dumps(final_result),
        }

    @urlmatch(netloc=FAKE_ES_HOST)
    def catchall_handler(url, request):
        print(
            "Unsupported URL: %s %s"
            % (
                request.method,
                url,
            )
        )
        return {"status_code": 501}

    handlers = [
        get_template,
        put_template,
        index_delete,
        index_lookup,
        post_doc,
        count_docs,
        lookup_docs,
        lookup_scroll,
        delete_scroll,
        catchall_handler,
    ]

    with HTTMock(*handlers):
        yield
