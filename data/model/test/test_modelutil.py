import pytest

from data.database import Role
from data.model.modelutil import paginate
from test.fixtures import *


@pytest.mark.parametrize(
    "page_size",
    [
        10,
        20,
        50,
        100,
        200,
        500,
        1000,
    ],
)
@pytest.mark.parametrize(
    "descending",
    [
        False,
        True,
    ],
)
def test_paginate(page_size, descending, initialized_db):
    # Add a bunch of rows into a test table (`Role`).
    for i in range(0, 522):
        Role.create(name="testrole%s" % i)

    query = Role.select().where(Role.name ** "testrole%")
    all_matching_roles = list(query)
    assert len(all_matching_roles) == 522

    # Paginate a query to lookup roles.
    collected = []
    page_token = None
    while True:
        results, page_token = paginate(
            query, Role, limit=page_size, descending=descending, page_token=page_token
        )
        assert len(results) <= page_size
        collected.extend(results)

        if page_token is None:
            break

        assert len(results) == page_size

        for index, result in enumerate(results[1:]):
            if descending:
                assert result.id < results[index].id
            else:
                assert result.id > results[index].id

    assert len(collected) == len(all_matching_roles)
    assert {c.id for c in collected} == {a.id for a in all_matching_roles}
