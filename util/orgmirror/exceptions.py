# -*- coding: utf-8 -*-
"""
Custom exceptions for registry adapters used in organization mirroring.
"""


class RegistryDiscoveryException(Exception):
    """
    Base exception for registry discovery errors.

    Raised when repository discovery fails due to network issues,
    authentication problems, or registry API errors.
    """

    def __init__(self, message: str, cause: Exception = None):
        """
        Initialize the exception.

        Args:
            message: Human-readable error description
            cause: Original exception that caused this error (optional)
        """
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message


class QuayDiscoveryException(RegistryDiscoveryException):
    """
    Exception raised when Quay registry discovery fails.

    This includes authentication failures, namespace not found,
    network issues, or API errors when listing repositories.
    """

    pass


class HarborDiscoveryException(RegistryDiscoveryException):
    """
    Exception raised when Harbor registry discovery fails.

    This includes authentication failures, project not found,
    network issues, or API errors when listing repositories.
    """

    pass
