from typing import Dict, Any
from pydantic import BaseModel
import datetime
import os
import yaml
import json
from loguru import logger

from .. import datasources
from ..utils import RedisKeyValueStore


class BaseDatasource:

    class Settings(BaseModel):
        datasource_class: str
        max_age_s: int = 0

    def __init__(self, settings_filename: str, kv_store: RedisKeyValueStore):
        self.id = os.path.splitext(os.path.basename(settings_filename))[0]
        self.settings_filename = settings_filename
        self.kv_store = kv_store
        self.kv_store.set_instance_key(self.id)
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_filename, 'r') as f:
                yaml_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading datasource config from {self.settings_filename}: {e}")
            return
        self.settings = self.Settings(**yaml_config)  # settings of the concrete (derived) class
        if (self.settings.datasource_class != self.__class__.__name__):
            logger.error(f"Error loading datasource config from {self.settings_filename}: class mismatch, expected {self.__class__.__name__} got {self.settings.datasource_class}")
            return
        logger.info(f"Configured datasource id={self.id} settings=({self.settings})")

    async def get_data(self):
        last_update = await self.kv_store.get_kv("last_update")
        last_update_at = datetime.datetime.fromisoformat(last_update) if last_update else None

        update_needed = last_update_at is None or self.settings is None or self.settings.max_age_s is None or self.settings.max_age_s <= 0
        if not update_needed:
            max_age = datetime.timedelta(seconds=self.settings.max_age_s)
            now = datetime.datetime.now(datetime.timezone.utc)
            update_needed = (now - last_update_at) >= max_age
        if update_needed:
            await self.update()
        data = await self.kv_store.get_kv_as_json("data")
        return data

    async def set_data(self, data: Dict[str, Any]):
        dt = datetime.datetime.now(datetime.timezone.utc)
        s = json.dumps(data)
        await self.kv_store.set_kv_from_dict({"last_update": dt.isoformat(), "data": s})

    async def update(self):
        """ Updates the data - overwrite this method to do the actual work!"""
        pass
