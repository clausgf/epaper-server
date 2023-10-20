from typing import Dict, Any
import aiohttp
import re
from loguru import logger

from .base import BaseDatasource
from ..utils import RedisKeyValueStore


BASE_URL = "https://api.openweathermap.org/data/2.5"


class WebScraperDatasource(BaseDatasource):

    class Settings(BaseDatasource.Settings):
        url: str
        find_expressions: list[str]

    def __init__(self, settings_filename: str, kv_store: RedisKeyValueStore):
        super().__init__(settings_filename, kv_store)
        self.session = aiohttp.ClientSession(raise_for_status=True)

    async def update(self):
        data = {}
        url = self.settings.url
        logger.info(f"Updating {self.id} in {self.__class__.__name__}, fetching {url}")
        try:
            async with self.session.get(url) as response:
                response_text = await response.text()

                for find_expression in self.settings.find_expressions:
                    match = re.search(find_expression, response_text)
                    if match:
                        data.update(match.groupdict(default={}))
                    else:
                        logger.info(f"... no match for '{find_expression}'")
        except Exception as e:
            import traceback
            logger.error(e)
            logger.error(traceback.format_exc())

        logger.debug(f"... collected data='{data}'")
        await self.set_data(data)
