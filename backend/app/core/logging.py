"""
Structured logging configuration for I-ITSM.

Provides a single ``setup_logging`` entry-point that configures Python's
built-in logging module with a consistent format across the application.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root application logger.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        The configured ``logging.Logger`` instance for the ``app`` namespace.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    # Configure the root 'app' logger so all child loggers (app.core, app.api, …)
    # inherit the configuration automatically.
    logger = logging.getLogger("app")
    logger.setLevel(numeric_level)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    return logger
