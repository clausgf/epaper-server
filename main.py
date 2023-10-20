import os
import sys
import logging
from uvicorn import Config, Server
from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages toward Loguru
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord):
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

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def init_logging(log_level):
    """
    Replaces logging handlers with a handler for using the custom handler.
    Inspired by https://gist.github.com/nkhitrov/a3e31cfcc1b19cba8e1b626276148c49
    """

    # disable handlers for specific uvicorn loggers to redirect their output to the default uvicorn logger
    # works with uvicorn==0.11.6
    loggers = (
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict
        if name.startswith("uvicorn.")
    )
    for uvicorn_logger in loggers:
        uvicorn_logger.handlers = []

    # change handler for default uvicorn logger
    intercept_handler = InterceptHandler()
    logging.getLogger("uvicorn").handlers = [intercept_handler]

    # set logs output, level and format
    logger.configure(
        handlers=[{"sink": sys.stdout, "level": LOG_LEVEL, "format": format_record}]
    )

    # old code - # setup logging
    # logging.root.handlers = [InterceptHandler()]
    # for name in logging.root.manager.loggerDict.keys():
    #     logging.getLogger(name).handlers = []
    #     logging.getLogger(name).propagate = True
    # logger.configure(handlers=[{
    #     "sink": sys.stdout, 
    #     "colorize": (not JSON_LOGS), 
    #     "serialize": JSON_LOGS,
    #     "level": LOG_LEVEL,
    # }])
    logging.root.setLevel(LOG_LEVEL)


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
    server.run()
