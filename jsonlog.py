import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone

SERVICE = "shop-api"
DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "app.log"
)


class JsonFormatter(logging.Formatter):
    """Turns one log record into ONE line of JSON with fixed fields."""

    def format(self, record: logging.LogRecord) -> str:
        tb = ""
        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(
            {
                "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                "level": record.levelname,
                "service": SERVICE,
                "message": record.getMessage(),
                "traceback": tb,
            }
        )


def get_logger() -> logging.Logger:
    path = os.environ.get("SHOP_LOG_PATH", DEFAULT_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    logger = logging.getLogger(SERVICE)
    if not logger.handlers:
        formatter = JsonFormatter()
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        console = logging.StreamHandler(sys.stderr)  # also visible in the Render log viewer
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(logging.ERROR)
        logger.propagate = False
    return logger