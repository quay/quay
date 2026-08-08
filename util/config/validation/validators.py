"""
Shared validator functions for config validation.
"""

import re
from typing import Any, List, Optional, Type
from urllib.parse import urlparse

from .errors import ValidationError


def validate_required_string(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is a non-empty string.

    Equivalent to Go's ValidateRequiredString.
    """
    if not value or not isinstance(value, str):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} is required",
        )
    return None


def validate_required_object(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is a non-None dict.

    Equivalent to Go's ValidateRequiredObject.
    """
    if value is None or not isinstance(value, dict):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} is required",
        )
    return None


def validate_is_hostname(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a string is a valid hostname with optional port.

    Equivalent to Go's ValidateIsHostname.
    """
    if not value:
        return None  # Let required validator handle empty

    if not isinstance(value, str):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a string",
        )

    # Pattern from Go: ^[a-zA-Z-0-9\.]+(:[0-9]+)?$
    pattern = r"^[a-zA-Z0-9\.\-]+(:[0-9]+)?$"
    if not re.match(pattern, value.strip()):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be of type Hostname",
        )
    return None


def validate_is_url(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a string is a valid URL.

    Equivalent to Go's ValidateIsURL.
    """
    if not value:
        return None

    if not isinstance(value, str):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a string",
        )

    try:
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Missing scheme or netloc")
    except Exception:
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be of type URL",
        )
    return None


def validate_is_one_of(
    value: Any,
    options: List[str],
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is one of the allowed options.

    Equivalent to Go's ValidateIsOneOfString.
    """
    if value is None:
        return None  # Let required validator handle missing

    if value not in options:
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be one of {', '.join(options)}.",
        )
    return None


def validate_at_least_one_of_string(
    values: List[Any],
    fields: List[str],
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that at least one of the given values is a non-empty string.

    Equivalent to Go's ValidateAtLeastOneOfString.
    """
    for val in values:
        if val and isinstance(val, str):
            return None

    return ValidationError(
        field_group=field_group,
        tags=fields,
        message=f"At least one of {', '.join(fields)} must be present",
    )


def validate_at_least_one_of_bool(
    values: List[bool],
    fields: List[str],
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that at least one of the given boolean values is True.

    Equivalent to Go's ValidateAtLeastOneOfBool.
    """
    for val in values:
        if val is True:
            return None

    return ValidationError(
        field_group=field_group,
        tags=fields,
        message=f"At least one of {', '.join(fields)} must be enabled",
    )


def validate_time_pattern(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate time pattern like '2w', '30d', '1h'.

    Pattern: ^[0-9]+(w|m|d|h|s)$
    Equivalent to Go's ValidateTimePattern.
    """
    if not value:
        return None

    if not isinstance(value, str):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a string",
        )

    pattern = r"^[0-9]+(w|m|d|h|s)$"
    if not re.match(pattern, value):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must have the regex pattern ^[0-9]+(w|m|d|h|s)$",
        )
    return None


def validate_is_type(
    value: Any,
    expected_type: Type,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is of the expected type.
    """
    if value is None:
        return None

    if not isinstance(value, expected_type):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be of type {expected_type.__name__}",
        )
    return None


def validate_port(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is a valid port number (1-65535).
    """
    if value is None:
        return None

    if not isinstance(value, int) or value < 1 or value > 65535:
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a port number between 1 and 65535",
        )
    return None


def validate_is_positive_int(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is a positive integer.
    """
    if value is None:
        return None

    if not isinstance(value, int) or value < 0:
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a positive integer",
        )
    return None


def validate_is_list(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a value is a list.
    """
    if value is None:
        return None

    if not isinstance(value, list):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a list",
        )
    return None


def validate_is_email(
    value: Any,
    field: str,
    field_group: str,
) -> Optional[ValidationError]:
    """
    Validate that a string is a valid email address format.
    """
    if not value:
        return None

    if not isinstance(value, str):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a string",
        )

    # Simple email pattern - not exhaustive but catches common issues
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, value):
        return ValidationError(
            field_group=field_group,
            tags=[field],
            message=f"{field} must be a valid email address",
        )
    return None
