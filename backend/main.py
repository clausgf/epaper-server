from fastapi import FastAPI, Request, Depends
import asyncio
import redis.asyncio as redis
import sys
import os
import glob
import yaml
import logging
from loguru import logger

from typing import Dict, Any
from .core.epaper import Epaper
from .core.settings import global_settings
from .core import datasources
from .core.datasources.base import BaseDatasource
from .routers import router
from .core.utils import RedisKeyValueStore

##############################################################################

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

##############################################################################

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
        # handlers=[{"sink": sys.stdout, "level": log_level, "format": format_record}]
        handlers=[{"sink": sys.stdout, "level": log_level}]
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
    #     "level": log_level,
    # }])
    logging.root.setLevel(log_level)

##############################################################################

class Context:
    count = 0

    def __init__(self, global_settings, redis, datasources, aliases, epapers):
        self.global_settings = global_settings
        self.redis = redis
        self.datasources = datasources
        self.aliases = aliases
        self.epapers = epapers

##############################################################################

def create_datasources(glob_pattern: str, redis) -> Dict[str, BaseDatasource]:
    logger.info(f"Creating datasources pattern={glob_pattern}")
    ds = {}
    filenames = glob.glob(glob_pattern)
    for fn in filenames:
        try:
            with open(fn, 'r') as f:
                yaml_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading datasource config from {fn}: {e}")
            continue

        ds_class_name = yaml_config['datasource_class']
        ds_class = getattr(datasources, ds_class_name, None)
        if ds_class is None:
            logger.error(f"Unknown datasource class {ds_class_name}")
            continue

        kv_store = RedisKeyValueStore(redis, ds_class_name)
        ds_instance = ds_class(fn, kv_store)
        ds[ds_instance.id] = ds_instance
    return ds


def create_epapers(glob_pattern: str, redis, datasources, aliases) -> Dict[str, Epaper]:
    logger.info(f"Creating epapers pattern={glob_pattern}")
    eps = {}
    filenames = glob.glob(glob_pattern)
    for fn in filenames:
        try:
            with open(fn, 'r') as f:
                yaml_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading epaper config from {fn}: {e}")
            continue

        kv_store = RedisKeyValueStore(redis, 'Epaper')
        epaper_instance = Epaper(fn, kv_store, datasources, aliases)
        eps[epaper_instance.id] = epaper_instance
    return eps


async def cyclic_func():
    while True:
        if app is not None and hasattr(app, 'context') and app.context:
            #logger.info(f"cyclic_func executing for: {app.context.epapers.keys()}")
            for epaper_id in app.context.epapers:
                try:
                    await app.context.epapers[epaper_id].update_if_needed()
                except Exception as e:
                    logger.exception(f"Error updating epaper {epaper_id}: {e}", exception=e)
        await asyncio.sleep(global_settings.cyclic_interval_s)

##############################################################################

init_logging(global_settings.log_level)
app = FastAPI(title='EPaper-Server')
app.include_router(router)
asyncio.ensure_future(cyclic_func())

@app.on_event('startup')
async def startup_event():
    logger.info("Starting up")
    _redis = await redis.from_url(global_settings.redis_url) # encoding='utf-8' decode_responses=True
    _datasources = create_datasources(global_settings.datasource_config_file_pattern, _redis)
    _aliases = {}
    _epapers = create_epapers(global_settings.epaper_config_file_pattern, _redis, _datasources, _aliases)
    app.context = Context(global_settings, _redis, _datasources, _aliases, _epapers)
