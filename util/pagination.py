import datetime
import json

from app import app
from util.security.crypto import encrypt_string, decrypt_string

# TTL (in seconds) for page tokens.
_PAGE_TOKEN_TTL = datetime.timedelta(days=2).total_seconds()


def decrypt_page_token(token_string):
    if token_string is None:
        return None

    unencrypted = decrypt_string(token_string, app.config["PAGE_TOKEN_KEY"], ttl=_PAGE_TOKEN_TTL)
    if unencrypted is None:
        return None

    try:
        return json.loads(unencrypted)
    except ValueError:
        return None


def encrypt_page_token(page_token):
    return encrypt_string(json.dumps(page_token), app.config["PAGE_TOKEN_KEY"])
