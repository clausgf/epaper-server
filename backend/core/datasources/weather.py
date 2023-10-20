from typing import Dict, Any
import aiohttp
from loguru import logger

from ..settings import global_settings
from .base import BaseDatasource
from ..utils import RedisKeyValueStore


BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherDatasource(BaseDatasource):

    class Settings(BaseDatasource.Settings):
        api_key: str
        city_id: str
        lat: float
        lon: float

    def __init__(self, settings_filename: str, kv_store: RedisKeyValueStore):
        super().__init__(settings_filename, kv_store)
        self.lang = global_settings.locale.split(".")[0]
        self.session = aiohttp.ClientSession(raise_for_status=True)

    async def update(self):
        # Fetch now
        #url = f"{BASE_URL}/weather?id={self.city_id}&units={self.units}&lang={self.lang}&APPID={self.api_key}"
        #logger.info(f"Fetching {url}")
        #response = requests.get(url)
        #response.raise_for_status()
        #self.now = response.json()

        # Fetch forecast
        #url = f"{BASE_URL}/forecast?id={self.city_id}&units={self.units}&lang={self.lang}&APPID={self.api_key}"
        #logger.info(f"Fetching {url}")
        #response = requests.get(url)
        #response.raise_for_status()
        #self.forecast = response.json()

        # Fetch one-call
        url = f"{BASE_URL}/onecall?units={global_settings.units}&lang={self.lang}&lat={self.settings.lat}&lon={self.settings.lon}&APPID={self.settings.api_key}"
        logger.info(f"Updating {self.id} in {self.__class__.__name__}, fetching {url}")
        async with self.session.get(url) as response:
            onecall = await response.json()
        await self.set_data(onecall)
