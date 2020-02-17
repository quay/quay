from abc import ABCMeta, abstractmethod, abstractproperty
from six import add_metaclass


class ConfigValidationException(Exception):
    """
    Exception raised when the configuration fails to validate for a known reason.
    """

    pass


@add_metaclass(ABCMeta)
class BaseValidator(object):
    @abstractproperty
    def name(self):
        """
        The key for the validation API.
        """
        pass

    @classmethod
    @abstractmethod
    def validate(cls, validator_context):
        """
        Raises Exception if failure to validate.
        """
        pass
