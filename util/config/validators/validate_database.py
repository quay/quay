from peewee import OperationalError

from data.database import validate_database_precondition
from util.config.validators import BaseValidator, ConfigValidationException


class DatabaseValidator(BaseValidator):
    name = "database"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates connecting to the database.
        """
        config = validator_context.config

        try:
            validate_database_precondition(config["DB_URI"], config.get("DB_CONNECTION_ARGS", {}))
        except OperationalError as ex:
            if ex.args and len(ex.args) > 1:
                raise ConfigValidationException(ex.args[1])
            else:
                raise ex
