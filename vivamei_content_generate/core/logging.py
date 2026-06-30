"""
core/logging.py

Application logging configuration.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure application-wide logging."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
