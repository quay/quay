import string
import re
import json

from text_unidecode import unidecode

from peewee import OperationalError

INVALID_PASSWORD_MESSAGE = (
    "Invalid password, password must be at least " + "8 characters and contain no whitespace."
)
VALID_CHARACTERS = string.digits + string.ascii_lowercase

MIN_USERNAME_LENGTH = 2
MAX_USERNAME_LENGTH = 255

VALID_LABEL_KEY_REGEX = r"^[a-z0-9](([a-z0-9]|[-.](?![.-]))*[a-z0-9])?$"
VALID_USERNAME_REGEX = r"^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
VALID_SERVICE_KEY_NAME_REGEX = r"^[\s a-zA-Z0-9\-_:/]*$"

INVALID_USERNAME_CHARACTERS = r"[^a-z0-9_]"


def validate_label_key(label_key):
    if len(label_key) > 255:
        return False

    return bool(re.match(VALID_LABEL_KEY_REGEX, label_key))


def validate_email(email_address):
    if not email_address:
        return False

    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))


def validate_username(username):
    # Based off the restrictions defined in the Docker Registry API spec
    if not re.match(VALID_USERNAME_REGEX, username):
        return (False, "Namespace must match expression " + VALID_USERNAME_REGEX)

    length_match = len(username) >= MIN_USERNAME_LENGTH and len(username) <= MAX_USERNAME_LENGTH
    if not length_match:
        return (
            False,
            "Namespace must be between %s and %s characters in length"
            % (MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH),
        )

    return (True, "")


def validate_password(password):
    # No whitespace and minimum length of 8
    if re.search(r"\s", password):
        return False
    return len(password) > 7


def _gen_filler_chars(num_filler_chars):
    if num_filler_chars == 0:
        yield ""
    else:
        for char in VALID_CHARACTERS:
            for suffix in _gen_filler_chars(num_filler_chars - 1):
                yield char + suffix


def generate_valid_usernames(input_username):
    if isinstance(input_username, bytes):
        try:
            input_username = input_username.decode("utf-8")
        except UnicodeDecodeError as ude:
            raise UnicodeDecodeError(
                "Username %s contains invalid characters: %s", input_username, ude
            )

    normalized = unidecode(input_username).strip().lower()
    prefix = re.sub(INVALID_USERNAME_CHARACTERS, "_", normalized)[:MAX_USERNAME_LENGTH]
    prefix = re.sub(r"_{2,}", "_", prefix)

    if prefix.endswith("_"):
        prefix = prefix[0 : len(prefix) - 1]

    while prefix.startswith("_"):
        prefix = prefix[1:]

    num_filler_chars = max(0, MIN_USERNAME_LENGTH - len(prefix))

    while num_filler_chars + len(prefix) <= MAX_USERNAME_LENGTH:
        for suffix in _gen_filler_chars(num_filler_chars):
            yield prefix + suffix
        num_filler_chars += 1


def is_json(value):
    if (value.startswith("{") and value.endswith("}")) or (
        value.startswith("[") and value.endswith("]")
    ):
        try:
            json.loads(value)
            return True
        except (TypeError, ValueError):
            return False
    return False


def validate_postgres_precondition(driver):
    cursor = driver.execute_sql("SELECT extname FROM pg_extension", ("public",))
    if "pg_trgm" not in [extname for extname, in cursor.fetchall()]:
        raise OperationalError(
            """
      "pg_trgm" extension does not exists in the database.
      Please run `CREATE EXTENSION IF NOT EXISTS pg_trgm;` as superuser on this database.
    """
        )


def validate_service_key_name(name):
    return name is None or bool(re.match(VALID_SERVICE_KEY_NAME_REGEX, name))
