def mysql_estimate_row_count(model_cls, db):
    """ Uses the information_schema to retrieve the row count for a table. """
    query = "SELECT table_rows FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s"
    cursor = db.execute_sql(query, (model_cls._meta.table_name,))
    res = cursor.fetchone()
    return res[0]


def normal_row_count(model_cls, db):
    """ Uses a normal .count() to retrieve the row count for a model. """
    return model_cls.select().count()
