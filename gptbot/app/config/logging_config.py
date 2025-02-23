import logging
import sys
from .config import Settings

def configure_logging():
    settings = Settings()
    logging_level = settings.LOG_LEVEL.upper()
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout
    )