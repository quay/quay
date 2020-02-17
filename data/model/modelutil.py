import dateutil.parser

from datetime import datetime

from peewee import SQL


def paginate(
    query,
    model,
    descending=False,
    page_token=None,
    limit=50,
    sort_field_alias=None,
    max_page=None,
    sort_field_name=None,
):
    """
    Paginates the given query using an field range, starting at the optional page_token.

    Returns a *list* of matching results along with an unencrypted page_token for the next page, if
    any. If descending is set to True, orders by the field descending rather than ascending.
    """
    # Note: We use the sort_field_alias for the order_by, but not the where below. The alias is
    # necessary for certain queries that use unions in MySQL, as it gets confused on which field
    # to order by. The where clause, on the other hand, cannot use the alias because Postgres does
    # not allow aliases in where clauses.
    sort_field_name = sort_field_name or "id"
    sort_field = getattr(model, sort_field_name)

    if sort_field_alias is not None:
        sort_field_name = sort_field_alias
        sort_field = SQL(sort_field_alias)

    if descending:
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field)

    start_index = pagination_start(page_token)
    if start_index is not None:
        if descending:
            query = query.where(sort_field <= start_index)
        else:
            query = query.where(sort_field >= start_index)

    query = query.limit(limit + 1)

    page_number = (page_token.get("page_number") or None) if page_token else None
    if page_number is not None and max_page is not None and page_number > max_page:
        return [], None

    return paginate_query(
        query, limit=limit, sort_field_name=sort_field_name, page_number=page_number
    )


def pagination_start(page_token=None):
    """
    Returns the start index for pagination for the given page token.

    Will return None if None.
    """
    if page_token is not None:
        start_index = page_token.get("start_index")
        if page_token.get("is_datetime"):
            start_index = dateutil.parser.parse(start_index)
        return start_index
    return None


def paginate_query(query, limit=50, sort_field_name=None, page_number=None):
    """
    Executes the given query and returns a page's worth of results, as well as the page token for
    the next page (if any).
    """
    results = list(query)
    page_token = None
    if len(results) > limit:
        start_index = getattr(results[limit], sort_field_name or "id")
        is_datetime = False
        if isinstance(start_index, datetime):
            start_index = start_index.isoformat() + "Z"
            is_datetime = True

        page_token = {
            "start_index": start_index,
            "page_number": page_number + 1 if page_number else 1,
            "is_datetime": is_datetime,
        }

    return results[0:limit], page_token
