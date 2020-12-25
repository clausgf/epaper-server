import pytest
import os

from ..core.datasources.base import BaseSource


REDIS_URL = os.environ.get("EPAPER_REDIS", 'redis://localhost')
TEST_DATASOURCE_TYPE = 'TestBaseDatasource'


@pytest.fixture(scope="module")
def config():
    config = {'source': TEST_DATASOURCE_TYPE, 'max_age': 3600}
    return config

@pytest.fixture(scope="function")
async def redis():
    import aioredis
    redis = await aioredis.create_redis_pool(REDIS_URL)
    yield redis
    async for key in redis.iscan(match=f'datasource:{TEST_DATASOURCE_TYPE}*'):
        print(f'Teardown redis: deleting {key}')
        await redis.delete(key)
    redis.close()
    await redis.wait_closed()
    print("Teardown redis: complete")

@pytest.mark.asyncio
async def test_last_update(config, redis):
    import datetime
    datasource = BaseSource(id='test_ds_id', config=config, redis=redis)
    timestamp_set = await datasource.set_last_update_timestamp_now()
    timestamp_get = await datasource.get_last_update_timestamp()
    print(f"set {timestamp_set}, got {timestamp_get}")
    assert abs(timestamp_set - timestamp_get) < datetime.timedelta(seconds=1)
