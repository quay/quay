import json
import re

from six import string_types

from jsonpath_rw import parse as parse_json_path
from jsonpath_rw.lexer import JsonPathLexerError

INLINE_PATH_PATTERN = r"\$\{([^}]*)\}"


class JSONTemplateParseException(Exception):
    """
    Exception raised if a JSON template could not be parsed.
    """


class JSONTemplate(object):
    """
    Represents a parsed template for producing JSON.
    """

    def __init__(self, template_string):
        try:
            self._parsed = json.loads(template_string)
        except ValueError as ve:
            raise JSONTemplateParseException("Could not parse template: %s" % ve)

        # Apply against an empty object to validate.
        self.apply({})

    def apply(self, data):
        return self._apply(self._parsed, data)

    def _apply(self, obj, data):
        if isinstance(obj, string_types):
            return self._process_string(obj, data)
        elif isinstance(obj, dict):
            return {
                self._process_string(key, data): self._apply(value, data)
                for key, value in obj.iteritems()
            }
        elif isinstance(obj, list):
            return [self._apply(item, data) for item in obj]
        else:
            return obj

    def _process_string(self, str_value, data):
        # Check for a direct match first.
        if re.match("^" + INLINE_PATH_PATTERN + "$", str_value):
            expression = str_value[2:-1]
            return self._process_inline(expression, data)

        def process_inline(match):
            result = self._process_inline(match.group(1), data)
            if result is None:
                return "(none)"

            if isinstance(result, list) and len(result) > 1:
                return ",".join(result)

            return str(result)

        return re.sub(INLINE_PATH_PATTERN, process_inline, str_value)

    def _process_inline(self, expression, data):
        if not expression:
            raise JSONTemplateParseException("Empty expression found")


def apply_data_to_obj(obj, data, missing="(none)"):
    if isinstance(obj, basestring):
        return _process_string(obj, data, missing)
    elif isinstance(obj, dict):
        return {
            _process_string(key, data, missing): apply_data_to_obj(value, data, missing)
            for key, value in obj.iteritems()
        }
    elif isinstance(obj, list):
        return [apply_data_to_obj(item, data, missing) for item in obj]
    else:
        return obj


def _process_string(str_value, data, missing_filler):
    # Check for a direct match first.
    if re.match("^" + INLINE_PATH_PATTERN + "$", str_value):
        expression = str_value[2:-1]
        return _process_inline(expression, data)

    def process_inline(match):
        result = _process_inline(match.group(1), data)
        if result is None:
            return missing_filler

        if isinstance(result, list) and len(result) > 1:
            return ",".join(result)

        return str(result)

    return re.sub(INLINE_PATH_PATTERN, process_inline, str_value)


def _process_inline(expression, data):
    if not expression:
        raise JSONTemplateParseException("Empty expression found")

    try:
        parsed = parse_json_path(expression)
    except JsonPathLexerError as jple:
        raise JSONTemplateParseException("For expression `%s`: %s" % (expression, jple))
    except Exception as ex:
        raise JSONTemplateParseException("For expression `%s`: %s" % (expression, ex))

    try:
        found = parsed.find(data)
        if not found:
            return None

        if len(found) > 1:
            return [f.data for f in found]

        return found[0].value
    except IndexError:
        return None
