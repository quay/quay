import pytest

from data.text import match_mysql, match_like
from data.database import Repository
from test.fixtures import *


@pytest.mark.parametrize(
    "input",
    [
        ("hello world"),
        ("hello ' world"),
        ('hello " world'),
        ("hello ` world"),
    ],
)
def test_mysql_text_escaping(input):
    query, values = Repository.select().where(match_mysql(Repository.description, input)).sql()
    assert input not in query


@pytest.mark.parametrize(
    "input, expected",
    [
        ("hello world", "hello world"),
        ("hello 'world", "hello world"),
        ('hello "world', "hello world"),
        ("hello `world", "hello world"),
        ("hello !world", "hello !!world"),
        ("hello %world", "hello !%world"),
    ],
)
def test_postgres_text_escaping(input, expected):
    query, values = Repository.select().where(match_like(Repository.description, input)).sql()
    assert input not in query
    assert values[0] == "%" + expected + "%"
