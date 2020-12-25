import datetime
import json
from loguru import logger

from ..utils import BaseRedis


class BaseDatasource(BaseRedis):

    def __init__(self, redis_pool, id, config):
        super().__init__(redis_pool=redis_pool, base_key="datasource", id=id)
        self.config = config
        self.max_age = datetime.timedelta(seconds=config.get('max_age', 0))

    async def get_data(self):
        last_update = await self.get_redis("last_update", encoding='utf-8')
        last_update_at = datetime.datetime.fromisoformat(last_update) if last_update else None

        update_needed = last_update_at is None or self.max_age is None
        if not update_needed:
            now = datetime.datetime.now(datetime.timezone.utc)
            update_needed = (now - last_update_at) >= self.max_age
        if update_needed:
            await self.update()
        data = await self.get_redis_json("data")
        return data

    async def set_data(self, data):
        dt = datetime.datetime.now(datetime.timezone.utc)
        s = json.dumps(data)
        await self.set_redis({"last_update": dt.isoformat(), "data": s})

    async def update(self):
        """ Updates the data - overwrite this method to do the actual work!"""
        pass
