import aiohttp
from loguru import logger
from .base import BaseDatasource


BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherDatasource(BaseDatasource):

    def __init__(self, redis_pool, id, config):
        super().__init__(redis_pool, id, config)
        self.city_id = config.get('city_id')
        self.lat = config.get('lat')
        self.lon = config.get('lon')
        self.units = config.get('units')
        self.lang = config["locale"].split("_")[0]
        self.api_key = config.get('api_key')

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
        url = f"{BASE_URL}/onecall?units={self.units}&lang={self.lang}&lat={self.lat}&lon={self.lon}&APPID={self.api_key}"
        logger.info(f"Fetching {url}")
        async with self.session.get(url) as response:
            onecall = await response.json()
            await self.set_data(onecall)
