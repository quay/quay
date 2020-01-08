# pylint: disable=protected-access

from functools import wraps, total_ordering


class FromDictionaryException(Exception):
    """
    Exception raised if constructing a data type from a dictionary fails due to missing data.
    """


def datatype(name, static_fields):
    """
    Defines a base class for a datatype that will represent a row from the database, in an
    abstracted form.
    """

    @total_ordering
    class DataType(object):
        __name__ = name

        def __init__(self, **kwargs):
            self._db_id = kwargs.pop("db_id", None)
            self._inputs = kwargs.pop("inputs", None)
            self._fields = kwargs

            for name in static_fields:
                assert name in self._fields, "Missing field %s" % name

        def __eq__(self, other):
            return self._db_id == other._db_id

        def __lt__(self, other):
            return self._db_id < other._db_id

        def __getattr__(self, name):
            if name in static_fields:
                return self._fields[name]

            raise AttributeError("Unknown field `%s`" % name)

        def __repr__(self):
            return "<%s> #%s" % (name, self._db_id)

        def __hash__(self):
            return hash((self.__name__, self._db_id))

        @classmethod
        def from_dict(cls, dict_data):
            try:
                return cls(**dict_data)
            except:
                raise FromDictionaryException()

        def asdict(self):
            dictionary_rep = dict(self._fields)
            assert "db_id" not in dictionary_rep and "inputs" not in dictionary_rep

            dictionary_rep["db_id"] = self._db_id
            dictionary_rep["inputs"] = self._inputs
            return dictionary_rep

    return DataType


def requiresinput(input_name):
    """
    Marks a property on the data type as requiring an input to be invoked.
    """

    def inner(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._inputs.get(input_name) is None:
                raise Exception("Cannot invoke function with missing input `%s`" % input_name)

            kwargs[input_name] = self._inputs[input_name]
            result = func(self, *args, **kwargs)
            return result

        return wrapper

    return inner


def optionalinput(input_name):
    """
    Marks a property on the data type as having an input be optional when invoked.
    """

    def inner(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            kwargs[input_name] = self._inputs.get(input_name)
            result = func(self, *args, **kwargs)
            return result

        return wrapper

    return inner
