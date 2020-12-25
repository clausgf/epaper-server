import aiohttp
import re
from loguru import logger
from .base import BaseDatasource


BASE_URL = "https://api.openweathermap.org/data/2.5"


class WebScraperDatasource(BaseDatasource):

    def __init__(self, redis_pool, id, config):
        super().__init__(redis_pool, id, config)
        self.url = config.get('url')
        self.find_expressions = config.get('find_expressions')
        self.session = aiohttp.ClientSession(raise_for_status=True)

    async def update(self):
        data = {}
        logger.info(f"Updating {self.id} in {self.__class__.__name__}, fetching {self.url}")
        async with self.session.get(self.url) as response:
            response_text = await response.text()

            for find_expression in self.find_expressions:
                match = re.search(find_expression, response_text)
                if match:
                    data.update(match.groupdict(default={}))
                else:
                    logger.info(f"... no match for '{find_expression}'")

        logger.debug(f"... collected data='{data}'")
        await self.set_data(data)
