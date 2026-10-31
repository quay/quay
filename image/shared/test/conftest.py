"""
Pytest configuration for image.shared tests.

Provides fixtures to prevent test pollution from logging state modifications.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def reset_logging():
    """
    Reset logging configuration after each test to prevent state pollution.

    This fixture ensures that tests which modify logger configuration
    (e.g., changing log levels, disabling propagation, adding handlers)
    do not affect subsequent tests.

    The fixture runs after each test in this directory and restores all
    loggers to their default state.
    """
    # Yield to run the test first
    yield

    # After test completes, reset all loggers to default state
    # This prevents logging configuration changes from leaking between tests
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        # Reset to NOTSET so it inherits from parent
        logger.setLevel(logging.NOTSET)
        # Ensure propagation is enabled (default)
        logger.propagate = True
        # Close and remove any handlers that were added
        # Must close handlers explicitly to release file descriptors
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    # Also reset the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # Python's default
    # Close and remove root logger handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
