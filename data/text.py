from peewee import NodeList, SQL, fn, TextField, Field


def _escape_wildcard(search_query):
    """
    Escapes the wildcards found in the given search query so that they are treated as *characters*
    rather than wildcards when passed to a LIKE or ILIKE clause with an ESCAPE '!'.
    """
    search_query = (
        search_query.replace("!", "!!").replace("%", "!%").replace("_", "!_").replace("[", "![")
    )

    # Just to be absolutely sure.
    search_query = search_query.replace("'", "")
    search_query = search_query.replace('"', "")
    search_query = search_query.replace("`", "")

    return search_query


def prefix_search(field, prefix_query):
    """
    Returns the wildcard match for searching for the given prefix query.
    """
    # Escape the known wildcard characters.
    prefix_query = _escape_wildcard(prefix_query)
    return Field.__pow__(field, NodeList((prefix_query + "%", SQL("ESCAPE '!'"))))


def match_mysql(field, search_query):
    """
    Generates a full-text match query using a Match operation, which is needed for MySQL.
    """
    if field.name.find("`") >= 0:  # Just to be safe.
        raise Exception("How did field name '%s' end up containing a backtick?" % field.name)

    # Note: There is a known bug in MySQL (https://bugs.mysql.com/bug.php?id=78485) that causes
    # queries of the form `*` to raise a parsing error. If found, simply filter out.
    search_query = search_query.replace("*", "")

    # Just to be absolutely sure.
    search_query = search_query.replace("'", "")
    search_query = search_query.replace('"', "")
    search_query = search_query.replace("`", "")

    return NodeList(
        (fn.MATCH(SQL("`%s`" % field.name)), fn.AGAINST(SQL("%s", [search_query]))), parens=True
    )


def match_like(field, search_query):
    """
    Generates a full-text match query using an ILIKE operation, which is needed for SQLite and
    Postgres.
    """
    escaped_query = _escape_wildcard(search_query)
    clause = NodeList(("%" + escaped_query + "%", SQL("ESCAPE '!'")))
    return Field.__pow__(field, clause)
