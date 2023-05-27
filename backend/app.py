from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
import asyncio
import aioredis
import paho.mqtt.client as mqtt
import os
import time
import datetime
import yaml
import babel
from typing import Optional
from loguru import logger

CONFIG_DIR = os.environ.get("EPAPER_CONFIGDIR", '/config')
CONFIG_FN = os.path.join(CONFIG_DIR, 'config.yml')
REDIS_URL = os.environ.get("EPAPER_REDIS", 'redis://redis')

from .core.display import Display
from .core import datasources
from .routers import router

app = FastAPI(title='EPaper-Server')
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")


def mqtt_on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"MQTT connected: userdata={userdata} flags={flags} rc={rc}")
    else:
        logger.error(f"MQTT connection error: userdata={userdata} flags={flags} rc={rc}")


def mqtt_on_disconnect(client, userdata, rc):
    if rc == 0:
        logger.info(f"MQTT disconnected: userdata={userdata} rc={rc}")
    else:
        logger.error(f"MQTT disconnection error: userdata={userdata} rc={rc}")


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

        self.mqtt_config = config["mqtt"]
        self.init_mqtt()

        self.CONFIG_DIR = CONFIG_DIR

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


    def init_mqtt(self):
        if "host" in self.mqtt_config.keys():
            client_id = self.mqtt_config.get("client_id", "epaper-server")
            host      = self.mqtt_config.get("host")
            port      = self.mqtt_config.get("port", 1883)
            username  = self.mqtt_config.get("username", None)
            password  = self.mqtt_config.get("password", None)

            logger.info(f"Connecting MQTT {host}:{port} client_id={client_id} username={username}")
            self.mqtt_client = mqtt.Client(client_id=client_id, clean_session=True)
            if username:
                self.mqtt_client.username_pw_set(username, password=password)
            self.mqtt_client.connect_async(host, port=port)
            #self.mqtt_client.enable_logger()
            self.mqtt_client.on_connect = mqtt_on_connect
            self.mqtt_client.on_disconnect = mqtt_on_disconnect
            self.mqtt_client.loop_start()

            self.mqtt_status_topic = self.mqtt_config.get("status_topic")

        else:
            self.mqtt_client = None
            self.mqtt_status_topic = None


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
