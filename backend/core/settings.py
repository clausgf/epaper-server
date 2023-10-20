from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Tuple


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='epaper.env')

    redis_url: str = "redis://redis"
    epaper_config_file_pattern: str = "./config/ep_*.yml"
    datasource_config_file_pattern: str = "./config/ds_*.yml"
    font_path: str = "backend/resources/fonts"
    icon_path: str = "backend/resources/icons"

    locale: str = 'de_DE.utf8'
    timezone: str = 'Europe/Berlin'
    units: Literal['metric', 'imperial'] = 'metric'
    date_format: str = 'EEEE, dd.MM.yyyy'

    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    cyclic_interval_s: int = 10


global_settings = Settings()
