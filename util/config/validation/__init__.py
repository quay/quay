"""
Config validation framework

This module provides config validation that can be run on startup and via API
against arbitrary config dictionaries.

Usage:
    from util.config.validation import validate_config, validate_config_or_raise

    # Get list of errors (empty list = valid)
    errors = validate_config(config_dict)

    # Or raise ValueError if invalid
    validate_config_or_raise(config_dict)
"""

from typing import Any, Dict, List

from .errors import ValidationError
from .fieldgroups import FIELD_GROUP_VALIDATORS

__all__ = [
    "ValidationError",
    "validate_config",
    "validate_config_or_raise",
]


def validate_config(config: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate a configuration dictionary against all field groups.

    Args:
        config: The configuration dictionary loaded from YAML

    Returns:
        List of ValidationError objects. Empty list means validation passed.
    """
    all_errors: List[ValidationError] = []

    for validator_func in FIELD_GROUP_VALIDATORS:
        errors = validator_func(config)
        all_errors.extend(errors)

    return all_errors


def validate_config_or_raise(config: Dict[str, Any]) -> None:
    """
    Validate configuration and raise an exception if invalid.

    Args:
        config: The configuration dictionary loaded from YAML

    Raises:
        ValueError: If validation fails, with all error messages
    """
    errors = validate_config(config)
    if errors:
        error_messages = "\n".join(f"  - [{e.field_group}] {e.message}" for e in errors)
        raise ValueError(f"Configuration validation failed:\n{error_messages}")
