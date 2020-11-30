# Adapted from https://gist.github.com/akaihola/1415730#file-streamingjson-py

# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:

#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.

#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.

#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import collections
import json
from json.encoder import encode_basestring, encode_basestring_ascii, INFINITY
from types import GeneratorType


FLOAT_REPR = str


class StreamingJSONEncoder(json.JSONEncoder):
    def iterencode(self, o, _one_shot=False):
        """
        Encode the given object and yield each string representation as available.

        For example::

          for chunk in StreamingJSONEncoder().iterencode(bigobject):
            mysocket.write(chunk)

        This method is a verbatim copy of
        :meth:`json.JSONEncoder.iterencode`.  It is
        needed because we need to call our patched
        :func:`streamingjsonencoder._make_iterencode`.
        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring

        def floatstr(
            o, allow_nan=self.allow_nan, _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY
        ):
            # Check for specials.  Note that this type of test is processor- and/or
            # platform-specific, so do tests which don't depend on the internals.

            if o != o:
                text = "NaN"
            elif o == _inf:
                text = "Infinity"
            elif o == _neginf:
                text = "-Infinity"
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError("Out of range float values are not JSON compliant: %r" % (o,))

            return text

        _iterencode = _make_iterencode(
            markers,
            self.default,
            _encoder,
            self.indent,
            floatstr,
            self.key_separator,
            self.item_separator,
            self.sort_keys,
            self.skipkeys,
            _one_shot,
        )
        return _iterencode(o, 0)


def _make_iterencode(
    markers,
    _default,
    _encoder,
    _indent,
    _floatstr,
    _key_separator,
    _item_separator,
    _sort_keys,
    _skipkeys,
    _one_shot,
    ValueError=ValueError,
    dict=dict,
    float=float,
    GeneratorType=GeneratorType,
    id=id,
    int=int,
    isinstance=isinstance,
    list=list,
    long=int,
    str=str,
    tuple=tuple,
):
    """
    This is a patched version of
    :func:`django.utils.simplejson.encoder.iterencode`.  Whenever it encounters
    a generator in the data structure, it encodes it as a JSON list.
    """

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            # note: empty generators aren't caught here, see below
            yield "[]"
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = "["
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = "\n" + (" " * (_indent * _current_indent_level))
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, str):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + "null"
            elif value is True:
                yield buf + "true"
            elif value is False:
                yield buf + "false"
            elif isinstance(value, int):
                yield buf + str(value)
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple, GeneratorType)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if first:
            # we had an empty generator
            yield buf
        if newline_indent is not None:
            _current_indent_level -= 1
            yield "\n" + (" " * (_indent * _current_indent_level))
        yield "]"
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield "{}"
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield "{"
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = "\n" + (" " * (_indent * _current_indent_level))
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = list(dct.items())
            items.sort(key=lambda kv: kv[0])
        else:
            items = iter(dct.items())
        for key, value in items:
            if isinstance(key, str):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = _floatstr(key)
            elif isinstance(key, int):
                key = str(key)
            elif key is True:
                key = "true"
            elif key is False:
                key = "false"
            elif key is None:
                key = "null"
            elif _skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, str):
                yield _encoder(value)
            elif value is None:
                yield "null"
            elif value is True:
                yield "true"
            elif value is False:
                yield "false"
            elif isinstance(value, int):
                yield str(value)
            elif isinstance(value, float):
                yield _floatstr(value)
            else:
                if isinstance(value, collections.Mapping):
                    chunks = _iterencode_dict(value, _current_indent_level)
                elif isinstance(value, collections.Iterable):
                    chunks = _iterencode_list(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield "\n" + (" " * (_indent * _current_indent_level))
        yield "}"
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, str):
            yield _encoder(o)
        elif o is None:
            yield "null"
        elif o is True:
            yield "true"
        elif o is False:
            yield "false"
        elif isinstance(o, int):
            yield str(o)
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, collections.Mapping):
            for chunk in _iterencode_dict(o, _current_indent_level):
                yield chunk
        elif isinstance(o, collections.Iterable):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
            if markers is not None:
                del markers[markerid]

    return _iterencode
