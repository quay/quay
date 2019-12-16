#!/usr/bin/env python
# -*- coding: utf-8 -*-


import datetime
import json
import logging
import re
import traceback


LOG_FORMAT_REGEXP = re.compile(r"\((.+?)\)", re.IGNORECASE)


def _json_default(obj):
    """
    Coerce everything to strings.

    All objects representing time get output as ISO8601.
    """
    if isinstance(obj, (datetime.date, datetime.time, datetime.datetime)):
        return obj.isoformat()

    elif isinstance(obj, Exception):
        return "Exception: %s" % str(obj)

    return str(obj)


# skip natural LogRecord attributes
# http://docs.python.org/library/logging.html#logrecord-attributes
RESERVED_ATTRS = set(
    [
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    ]
)


class JsonFormatter(logging.Formatter):
    """
    A custom formatter to format logging records as json strings.

    extra values will be formatted as str() if nor supported by json default encoder
    """

    def __init__(self, *args, **kwargs):
        """
        :param json_default: a function for encoding non-standard objects
            as outlined in http://docs.python.org/2/library/json.html
        :param json_encoder: optional custom encoder
        :param json_serializer: a :meth:`json.dumps`-compatible callable
            that will be used to serialize the log record.
        :param prefix: an optional key prefix to nest logs
        """
        self.json_default = kwargs.pop("json_default", _json_default)
        self.json_encoder = kwargs.pop("json_encoder", None)
        self.json_serializer = kwargs.pop("json_serializer", json.dumps)
        self.default_values = kwargs.pop("default_extra", {})
        self.prefix_key = kwargs.pop("prefix_key", "data")

        logging.Formatter.__init__(self, *args, **kwargs)

        self._fmt_parameters = self._parse_format_string()
        self._skip_fields = set(self._fmt_parameters)
        self._skip_fields.update(RESERVED_ATTRS)

    def _parse_format_string(self):
        """
        Parses format string looking for substitutions.
        """
        standard_formatters = LOG_FORMAT_REGEXP
        return standard_formatters.findall(self._fmt)

    def add_fields(self, log_record, record, message_dict):
        """
        Override this method to implement custom logic for adding fields.
        """

        target = log_record
        if self.prefix_key:
            log_record[self.prefix_key] = {}
            target = log_record[self.prefix_key]

        for field, value in record.__dict__.items():
            if field in self._fmt_parameters and field in RESERVED_ATTRS:
                log_record[field] = value
            elif field not in RESERVED_ATTRS:
                target[field] = value

        target.update(message_dict)
        target.update(self.default_values)

    def format(self, record):
        """
        Formats a log record and serializes to json.
        """
        message_dict = {}
        if isinstance(record.msg, dict):
            message_dict = record.msg
            record.message = None
            if "message" in message_dict:
                record.message = message_dict.pop("message", "")
        else:
            record.message = record.getMessage()

        # only format time if needed
        if "asctime" in self._fmt_parameters:
            record.asctime = self.formatTime(record, self.datefmt)

        # Display formatted exception, but allow overriding it in the
        # user-supplied dict.
        if record.exc_info and not message_dict.get("exc_info"):
            message_dict["exc_info"] = traceback.format_list(
                traceback.extract_tb(record.exc_info[2])
            )
        log_record = {}

        self.add_fields(log_record, record, message_dict)

        return self.json_serializer(log_record, default=self.json_default, cls=self.json_encoder)
