import json
import re
import string
from typing import Any, Generator, Optional, Tuple, Union

from peewee import OperationalError
from text_unidecode import unidecode

INVALID_PASSWORD_MESSAGE = (
    "Invalid password, password must be at least " + "8 characters and contain no whitespace."
)
VALID_CHARACTERS = string.digits + string.ascii_lowercase

MIN_USERNAME_LENGTH = 2
MAX_USERNAME_LENGTH = 255

VALID_LABEL_KEY_REGEX = r"^[a-z0-9](([a-z0-9]|[-.](?![.-]))*[a-z0-9])?$"
VALID_USERNAME_REGEX = r"^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
VALID_SERVICE_KEY_NAME_REGEX = r"^[\s a-zA-Z0-9\-_:/]*$"

INVALID_USERNAME_CHARACTERS = r"[^a-z0-9_-]"


def validate_label_key(label_key: str) -> bool:
    """
    Validate a label key according to Kubernetes label key constraints.
    
    Args:
        label_key: The label key to validate
        
    Returns:
        True if the label key is valid, False otherwise
    """
    if len(label_key) > 255:
        return False

    return bool(re.match(VALID_LABEL_KEY_REGEX, label_key))


def validate_email(email_address: str) -> bool:
    """
    Validate an email address using basic regex pattern.
    
    Args:
        email_address: The email address to validate
        
    Returns:
        True if the email address has a valid format, False otherwise
    """
    if not email_address:
        return False

    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate a username according to Docker Registry API spec restrictions.
    
    Args:
        username: The username to validate
        
    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is empty.
    """
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


def validate_password(password: str) -> bool:
    """
    Validate a password meets minimum security requirements.
    
    Args:
        password: The password to validate
        
    Returns:
        True if password is valid (no whitespace, minimum 8 characters), False otherwise
    """
    # No whitespace and minimum length of 8
    if re.search(r"\s", password):
        return False
    return len(password) > 7


def validate_robot_token(token: str) -> bool:
    """
    Validate a robot token format.
    
    Args:
        token: The robot token to validate
        
    Returns:
        True if token is exactly 64 characters of uppercase letters and digits, False otherwise
    """
    if len(token) != 64:
        return False

    for t in token:
        if t not in string.ascii_uppercase + string.digits:
            return False

    return True


def _gen_filler_chars(num_filler_chars: int) -> Generator[str, None, None]:
    """
    Generate all possible filler character combinations of a given length.
    
    Args:
        num_filler_chars: Number of filler characters to generate
        
    Yields:
        All possible character combinations using VALID_CHARACTERS
    """
    if num_filler_chars == 0:
        yield ""
    else:
        for char in VALID_CHARACTERS:
            for suffix in _gen_filler_chars(num_filler_chars - 1):
                yield char + suffix


def generate_valid_usernames(input_username: Union[str, bytes]) -> Generator[str, None, None]:
    """
    Generate valid usernames based on an input username by normalizing and adding suffixes.
    
    Args:
        input_username: The input username to normalize (can be string or bytes)
        
    Yields:
        Valid usernames that comply with username validation rules
        
    Raises:
        UnicodeDecodeError: If input_username bytes cannot be decoded as UTF-8
    """
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


def is_json(value: str) -> bool:
    """
    Check if a string contains valid JSON.
    
    Args:
        value: The string to check for valid JSON format
        
    Returns:
        True if the string is valid JSON (object or array), False otherwise
    """
    if (value.startswith("{") and value.endswith("}")) or (
        value.startswith("[") and value.endswith("]")
    ):
        try:
            json.loads(value)
            return True
        except (TypeError, ValueError):
            return False
    return False


def validate_postgres_precondition(driver: Any) -> None:
    """
    Validate that required PostgreSQL extensions are installed.
    
    Args:
        driver: Database driver/connection object
        
    Raises:
        OperationalError: If pg_trgm extension is not installed
    """
    cursor = driver.execute_sql("SELECT extname FROM pg_extension", ("public",))
    if "pg_trgm" not in [extname for extname, in cursor.fetchall()]:
        raise OperationalError(
            """
      "pg_trgm" extension does not exists in the database.
      Please run `CREATE EXTENSION IF NOT EXISTS pg_trgm;` as superuser on this database.
    """
        )


def validate_service_key_name(name: Optional[str]) -> bool:
    """
    Validate a service key name format.
    
    Args:
        name: The service key name to validate (can be None)
        
    Returns:
        True if name is None or matches the valid service key name regex, False otherwise
    """
    return name is None or bool(re.match(VALID_SERVICE_KEY_NAME_REGEX, name))
