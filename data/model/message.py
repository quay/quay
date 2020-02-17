from data.database import Messages, MediaType


def get_messages():
    """
    Query the data base for messages and returns a container of database message objects.
    """
    return Messages.select(Messages, MediaType).join(MediaType)


def create(messages):
    """
    Insert messages into the database.
    """
    inserted = []
    for message in messages:
        severity = message["severity"]
        media_type_name = message["media_type"]
        media_type = MediaType.get(name=media_type_name)

        inserted.append(
            Messages.create(content=message["content"], media_type=media_type, severity=severity)
        )
    return inserted


def delete_message(uuids):
    """
    Delete message from the database.
    """
    if not uuids:
        return
    Messages.delete().where(Messages.uuid << uuids).execute()
