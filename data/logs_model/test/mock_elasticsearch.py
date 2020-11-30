# -*- coding: utf-8 -*-
import json

from datetime import datetime
from dateutil.parser import parse

from data.logs_model.datatypes import LogEntriesPage, Log, AggregatedLogCount


def _status(d, code=200):
    return {"status_code": code, "content": json.dumps(d)}


def _shards(d, total=5, failed=0, successful=5):
    d.update({"_shards": {"total": total, "failed": failed, "successful": successful}})
    return d


def _hits(hits):
    return {"hits": {"total": len(hits), "max_score": None, "hits": hits}}


INDEX_LIST_RESPONSE_HIT1_HIT2 = _status({"logentry_2018-03-08": {}, "logentry_2018-04-02": {}})


INDEX_LIST_RESPONSE_HIT2 = _status({"logentry_2018-04-02": {}})


INDEX_LIST_RESPONSE = _status(
    {
        "logentry_2019-01-01": {},
        "logentry_2017-03-08": {},
        "logentry_2018-03-08": {},
        "logentry_2018-04-02": {},
    }
)


DEFAULT_TEMPLATE_RESPONSE = _status({"acknowledged": True})
INDEX_RESPONSE_2019_01_01 = _status(
    _shards(
        {
            "_index": "logentry_2019-01-01",
            "_type": "_doc",
            "_id": "1",
            "_version": 1,
            "_seq_no": 0,
            "_primary_term": 1,
            "result": "created",
        }
    )
)

INDEX_RESPONSE_2017_03_08 = _status(
    _shards(
        {
            "_index": "logentry_2017-03-08",
            "_type": "_doc",
            "_id": "1",
            "_version": 1,
            "_seq_no": 0,
            "_primary_term": 1,
            "result": "created",
        }
    )
)

FAILURE_400 = _status({}, 400)

INDEX_REQUEST_2019_01_01 = [
    "logentry_2019-01-01",
    {
        "account_id": 1,
        "repository_id": 1,
        "ip": "192.168.1.1",
        "random_id": 233,
        "datetime": "2019-01-01T03:30:00",
        "metadata": {"key": "value", "time": "2018-03-08T03:30:00", "😂": "😂👌👌👌👌"},
        "performer_id": 1,
        "kind_id": 1,
    },
]

INDEX_REQUEST_2017_03_08 = [
    "logentry_2017-03-08",
    {
        "repository_id": 1,
        "account_id": 1,
        "ip": "192.168.1.1",
        "random_id": 233,
        "datetime": "2017-03-08T03:30:00",
        "metadata": {"key": "value", "time": "2018-03-08T03:30:00", "😂": "😂👌👌👌👌"},
        "performer_id": 1,
        "kind_id": 2,
    },
]

_hit1 = {
    "_index": "logentry_2018-03-08",
    "_type": "doc",
    "_id": "1",
    "_score": None,
    "_source": {
        "random_id": 233,
        "kind_id": 1,
        "account_id": 1,
        "performer_id": 1,
        "repository_id": 1,
        "ip": "192.168.1.1",
        "metadata_json": '{"\\ud83d\\ude02": "\\ud83d\\ude02\\ud83d\\udc4c\\ud83d\\udc4c\\ud83d\\udc4c\\ud83d\\udc4c", "key": "value", "time": 1520479800}',
        "datetime": "2018-03-08T03:30",
    },
    "sort": [1520479800000, 233],
}

_hit2 = {
    "_index": "logentry_2018-04-02",
    "_type": "doc",
    "_id": "2",
    "_score": None,
    "_source": {
        "random_id": 233,
        "kind_id": 2,
        "account_id": 1,
        "performer_id": 1,
        "repository_id": 1,
        "ip": "192.168.1.2",
        "metadata_json": '{"\\ud83d\\ude02": "\\ud83d\\ude02\\ud83d\\udc4c\\ud83d\\udc4c\\ud83d\\udc4c\\ud83d\\udc4c", "key": "value", "time": 1522639800}',
        "datetime": "2018-04-02T03:30",
    },
    "sort": [1522639800000, 233],
}

_log1 = Log(
    "{}",
    "192.168.1.1",
    parse("2018-03-08T03:30"),
    "user1.email",
    "user1.username",
    "user1.robot",
    "user1.organization",
    "user1.username",
    "user1.email",
    "user1.robot",
    1,
)
_log2 = Log(
    "{}",
    "192.168.1.2",
    parse("2018-04-02T03:30"),
    "user1.email",
    "user1.username",
    "user1.robot",
    "user1.organization",
    "user1.username",
    "user1.email",
    "user1.robot",
    2,
)

SEARCH_RESPONSE_START = _status(_shards(_hits([_hit1, _hit2])))
SEARCH_RESPONSE_END = _status(_shards(_hits([_hit2])))
SEARCH_REQUEST_START = {
    "sort": [{"datetime": "desc"}, {"random_id.keyword": "desc"}],
    "query": {"bool": {"filter": [{"term": {"performer_id": 1}}, {"term": {"repository_id": 1}}]}},
    "size": 2,
}
SEARCH_REQUEST_END = {
    "sort": [{"datetime": "desc"}, {"random_id.keyword": "desc"}],
    "query": {"bool": {"filter": [{"term": {"performer_id": 1}}, {"term": {"repository_id": 1}}]}},
    "search_after": [1520479800000, 233],
    "size": 2,
}
SEARCH_REQUEST_FILTER = {
    "sort": [{"datetime": "desc"}, {"random_id.keyword": "desc"}],
    "query": {
        "bool": {
            "filter": [
                {"term": {"performer_id": 1}},
                {"term": {"repository_id": 1}},
                {"bool": {"must_not": [{"terms": {"kind_id": [1]}}]}},
            ]
        }
    },
    "size": 2,
}
SEARCH_PAGE_TOKEN = {
    "datetime": datetime(2018, 3, 8, 3, 30).isoformat(),
    "random_id": 233,
    "page_number": 1,
}
SEARCH_PAGE_START = LogEntriesPage(logs=[_log1], next_page_token=SEARCH_PAGE_TOKEN)
SEARCH_PAGE_END = LogEntriesPage(logs=[_log2], next_page_token=None)
SEARCH_PAGE_EMPTY = LogEntriesPage([], None)

AGGS_RESPONSE = _status(
    _shards(
        {
            "hits": {"total": 4, "max_score": None, "hits": []},
            "aggregations": {
                "by_id": {
                    "doc_count_error_upper_bound": 0,
                    "sum_other_doc_count": 0,
                    "buckets": [
                        {
                            "key": 2,
                            "doc_count": 3,
                            "by_date": {
                                "buckets": [
                                    {
                                        "key_as_string": "2009-11-12T00:00:00.000Z",
                                        "key": 1257984000000,
                                        "doc_count": 1,
                                    },
                                    {
                                        "key_as_string": "2009-11-13T00:00:00.000Z",
                                        "key": 1258070400000,
                                        "doc_count": 0,
                                    },
                                    {
                                        "key_as_string": "2009-11-14T00:00:00.000Z",
                                        "key": 1258156800000,
                                        "doc_count": 2,
                                    },
                                ]
                            },
                        },
                        {
                            "key": 1,
                            "doc_count": 1,
                            "by_date": {
                                "buckets": [
                                    {
                                        "key_as_string": "2009-11-15T00:00:00.000Z",
                                        "key": 1258243200000,
                                        "doc_count": 1,
                                    }
                                ]
                            },
                        },
                    ],
                }
            },
        }
    )
)

AGGS_REQUEST = {
    "query": {
        "bool": {
            "filter": [
                {"term": {"performer_id": 1}},
                {"term": {"repository_id": 1}},
                {"bool": {"must_not": [{"terms": {"kind_id": [2]}}]}},
            ],
            "must": [
                {"range": {"datetime": {"lt": "2018-04-08T03:30:00", "gte": "2018-03-08T03:30:00"}}}
            ],
        }
    },
    "aggs": {
        "by_id": {
            "terms": {"field": "kind_id"},
            "aggs": {"by_date": {"date_histogram": {"field": "datetime", "interval": "day"}}},
        }
    },
    "size": 0,
}

AGGS_COUNT = [
    AggregatedLogCount(1, 1, parse("2009-11-15T00:00:00.000")),
    AggregatedLogCount(2, 1, parse("2009-11-12T00:00:00.000")),
    AggregatedLogCount(2, 2, parse("2009-11-14T00:00:00.000")),
]

COUNT_REQUEST = {"query": {"bool": {"filter": [{"term": {"repository_id": 1}}]}}}
COUNT_RESPONSE = _status(
    _shards(
        {
            "count": 1,
        }
    )
)

# assume there are 2 pages
_scroll_id = "DnF1ZXJ5VGhlbkZldGNoBQAAAAAAACEmFkk1aGlTRzdSUWllejZmYTlEYTN3SVEAAAAAAAAhJRZJNWhpU0c3UlFpZXo2ZmE5RGEzd0lRAAAAAAAAHtAWLWZpaFZXVzVSTy1OTXA5V3MwcHZrZwAAAAAAAB7RFi1maWhWV1c1Uk8tTk1wOVdzMHB2a2cAAAAAAAAhJxZJNWhpU0c3UlFpZXo2ZmE5RGEzd0lR"


def _scroll(d):
    d["_scroll_id"] = _scroll_id
    return d


SCROLL_CREATE = _status(_shards(_scroll(_hits([_hit1]))))
SCROLL_GET = _status(_shards(_scroll(_hits([_hit2]))))
SCROLL_GET_2 = _status(_shards(_scroll(_hits([]))))
SCROLL_DELETE = _status({"succeeded": True, "num_freed": 5})
SCROLL_LOGS = [[_log1], [_log2]]

SCROLL_REQUESTS = [
    [
        "5m",
        1,
        {
            "sort": "_doc",
            "query": {
                "range": {"datetime": {"lt": "2018-04-02T00:00:00", "gte": "2018-03-08T00:00:00"}}
            },
        },
    ],
    [{"scroll": "5m", "scroll_id": _scroll_id}],
    [{"scroll": "5m", "scroll_id": _scroll_id}],
    [{"scroll_id": [_scroll_id]}],
]

SCROLL_RESPONSES = [SCROLL_CREATE, SCROLL_GET, SCROLL_GET_2, SCROLL_DELETE]
