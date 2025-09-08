"""Top-level package for committee_manager."""

import logging

__author__ = "Example Author"
__email__ = "author@example.com"
__version__ = "0.1.0"

logger = logging.getLogger("committee_manager")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

__all__ = ["logger"]
