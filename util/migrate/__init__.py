import logging

from sqlalchemy.types import TypeDecorator, Text, String
from sqlalchemy.dialects.mysql import TEXT as MySQLText, LONGTEXT, VARCHAR as MySQLString


logger = logging.getLogger(__name__)


class UTF8LongText(TypeDecorator):
    """
    Platform-independent UTF-8 LONGTEXT type.

    Uses MySQL's LongText with charset utf8mb4, otherwise uses TEXT, because other engines default
    to UTF-8 and have longer TEXT fields.
    """

    impl = Text

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(
                LONGTEXT(charset="utf8mb4", collation="utf8mb4_unicode_ci")
            )
        else:
            return dialect.type_descriptor(Text())


class UTF8CharField(TypeDecorator):
    """
    Platform-independent UTF-8 Char type.

    Uses MySQL's VARCHAR with charset utf8mb4, otherwise uses String, because other engines default
    to UTF-8.
    """

    impl = String

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(
                MySQLString(
                    charset="utf8mb4", collation="utf8mb4_unicode_ci", length=self.impl.length
                )
            )
        else:
            return dialect.type_descriptor(String(length=self.impl.length))
