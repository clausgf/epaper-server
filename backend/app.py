from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
import asyncio
import aioredis
import os
import time
import datetime
import yaml
import babel
from typing import Optional
from loguru import logger

CONFIG_FN = os.environ.get("EPAPER_CONFIGFILE", 'config.yml')
REDIS_URL = os.environ.get("EPAPER_REDIS", 'redis://redis')

from .core.display import Display
from .core import datasources
from .routers import router

app = FastAPI(title='EPaper-Server')
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")


class Context:
    count = 0

    def __init__(self, config_fn, redis):
        self.datasources = {}
        self.displays = {}
        self.aliases = {}
        self.redis = redis

        with open(config_fn) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logger.info(f"Loaded configuration from file {config_fn}")
        logger.debug(f"Configuration is {config}")

        default_settings = config["default_settings"]

        for datasource_id, datasource_config in config["datasources"].items():
            datasource_class = getattr(datasources, datasource_config['class'] + 'Datasource')
            datasource_config = {**default_settings, **datasource_config}
            datasource_obj = datasource_class(redis, datasource_id, datasource_config)
            self.datasources[datasource_id] = datasource_obj

        for display_id, display_config in config["displays"].items():
            self.displays[display_id] = Display(redis, display_id, default_settings, display_config, self.datasources)

        for alias_id, alias_display_id in config["aliases"].items():
            self.displays[alias_display_id].aliases.append(alias_id)
            self.aliases[alias_id] = alias_display_id


@app.on_event('startup')
async def setup():
    logger.info("Connecting to REDIS")
    app.redis_pool = await aioredis.create_redis_pool(REDIS_URL)
    logger.info("Creating Context")
    app.context = Context(CONFIG_FN, app.redis_pool)


async def cyclic_func():
    while True:
        if app is not None and hasattr(app, 'redis_pool') and app.redis_pool:
            redis = app.redis_pool
            if hasattr(app, 'context') and app.context:
                context = app.context
                for key in context.displays:
                    await context.displays[key].update_if_needed()
        await asyncio.sleep(10)


asyncio.ensure_future(cyclic_func())
