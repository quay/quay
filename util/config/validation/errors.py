"""
Validation error types for config validation.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ValidationError:
    """
    Represents a validation error for a config field group.
    """

    field_group: str
    tags: List[str]  # Field names involved in the error
    message: str

    def __str__(self) -> str:
        return self.message
