import os
import sys
import logging
from uvicorn import Config, Server
from loguru import logger


HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
DEBUG = True if os.environ.get("DEBUG", "1") == "1" else False
LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
JSON_LOGS = True if os.environ.get("JSON_LOGS", "0") == "1" else False


# Logging configuration from
# https://pawamoy.github.io/posts/unify-logging-for-a-gunicorn-uvicorn-app/#uvicorn-only-version
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


if __name__ == "__main__":

    server = Server(
        Config(
            "backend.app:app",
            host=HOST,
            port=PORT,
            reload=True,
            debug=DEBUG,
            log_level=LOG_LEVEL,
        )
    )

    # setup logging
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(LOG_LEVEL)
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    logger.configure(handlers=[{
        "sink": sys.stdout, 
        "colorize": (not JSON_LOGS), 
        "serialize": JSON_LOGS,
        "level": LOG_LEVEL,
    }])

    server.run()
