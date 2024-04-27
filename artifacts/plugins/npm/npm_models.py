import uuid
from datetime import datetime
from hashlib import sha512

from peewee import CharField, BooleanField, DateTimeField
from playhouse.postgres_ext import ArrayField

from data.database import BaseModel, QuayUserField, db_transaction, User


class NpmToken(BaseModel):
    token_name = CharField()
    token_key = CharField()
    read_only = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    cidr_whitelist = ArrayField(CharField, null=True)
    user = QuayUserField(allows_robots=False)


def create_and_save_new_token_for_user(current_user, read_only=False):
    token_value = str(uuid.uuid4())
    token_key = sha512(token_value.encode('utf-8')).hexdigest()
    user = User.get(username=current_user.username)
    token = NpmToken(token_name=token_key, token_key=token_key, read_only=read_only, user=user)
    token.save()
    return token_value


