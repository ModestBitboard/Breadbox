"""
I'll admit, this logger is really awful.
Of all parts of the system, this would probably be the easiest to improve.
"""

import logging
from rich.logging import RichHandler
import sys

FORMAT = "%(message)s"

logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(
        markup=True,
        rich_tracebacks=True
    )]
)

logging.captureWarnings(True)

log = logging.getLogger("breadbox")


# noinspection PyShadowingBuiltins,PyUnusedLocal
def except_handler(type, value, tb):
    log.exception(str(value))


sys.excepthook = except_handler
