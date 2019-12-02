def copy_table_contents(source_table, destination_table, conn):
    if conn.engine.name == "postgresql":
        conn.execute('INSERT INTO "%s" SELECT * FROM "%s"' % (destination_table, source_table))
        result = list(conn.execute('Select Max(id) from "%s"' % destination_table))[0]
        if result[0] is not None:
            new_start_id = result[0] + 1
            conn.execute(
                'ALTER SEQUENCE "%s_id_seq" RESTART WITH %s' % (destination_table, new_start_id)
            )
    else:
        conn.execute(
            "INSERT INTO `%s` SELECT * FROM `%s` WHERE 1" % (destination_table, source_table)
        )
        result = list(conn.execute("Select Max(id) from `%s` WHERE 1" % destination_table))[0]
        if result[0] is not None:
            new_start_id = result[0] + 1
            conn.execute("ALTER TABLE `%s` AUTO_INCREMENT = %s" % (destination_table, new_start_id))
