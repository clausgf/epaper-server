from pydantic import BaseModel, Field
from typing import Tuple, Dict, List, Tuple, Union, Annotated
from PIL import Image, ImageChops, ImagePalette
import random
import string
import datetime
import io
import os
import yaml
from loguru import logger
from . import widgets
from .widgets.base import BaseWidget
from .widgets.text import TextWidgetSettings
from .widgets.date import DateWidgetSettings
from .widgets.weather import WeatherNowWidgetSettings, WeatherForecastWidgetSettings, WeatherPrecipitationWidgetSettings, WeatherTemperatureWidgetSettings
from .settings import global_settings
from .drawingcontext import DrawingContext
from .datasources.base import BaseDatasource
from .utils import RedisKeyValueStore


AnyWidget = Annotated[Union[TextWidgetSettings, 
                            DateWidgetSettings, 
                            WeatherNowWidgetSettings, 
                            WeatherForecastWidgetSettings, WeatherPrecipitationWidgetSettings, WeatherTemperatureWidgetSettings
                           ], Field(discriminator="widget_class")]


class EpaperSettings(BaseModel):
    size: Tuple[int, int]
    bits_per_pixel: int
    colors: List[Tuple[int, int, int]]
    rotation: int = 0
    update_interval_s: int = 3600   # 0 = update on every request
    client_update_delay_s: int = 30
    font: Tuple[str, int] = ("Roboto-Regular.ttf", 16)
    widgets: List[AnyWidget] = []
    aliases: List[str] = []


class Epaper:

    def __init__(self, settings_filename: str, kv_store: RedisKeyValueStore, datasources: Dict[str, BaseDatasource]):
        self.id = os.path.splitext(os.path.basename(settings_filename))[0]
        self.settings_filename = settings_filename
        self.kv_store = kv_store
        self.kv_store.set_instance_key(self.id)
        self.datasources = datasources
        self.debug = False  # True
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_filename, 'r') as f:
                yaml_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading epaper config from {self.settings_filename}: {e}")
            return
        self.settings = EpaperSettings(**yaml_config)

        # create widgets
        self.widgets = []
        for id, widget_config in enumerate(self.settings.widgets):
            logger.info(f"creating widget {widget_config}")
            # inject default values if not set
            widget_config.colors = widget_config.colors if widget_config.colors else self.settings.colors
            widget_config.font = widget_config.font if widget_config.font else self.settings.font
            _datasource  = self.datasources.get(widget_config.datasource) if widget_config.datasource else None
            widget_class = getattr(widgets, widget_config.widget_class, None)
            if widget_class is None:
                logger.error(f"Unknown widget class {widget_config.widget_class}")
                continue
            widget_obj   = widget_class(id, widget_config, _datasource)
            self.widgets.append(widget_obj)
        
        # update configuration shortcuts
        self.update_interval     = datetime.timedelta(seconds=self.settings.update_interval_s)
        self.client_update_delay = datetime.timedelta(seconds=self.settings.client_update_delay_s)
        logger.info(f"Configured epaper id={self.id} settings=({self.settings})")


    async def get_image(self):
        image_data = await self.kv_store.get_kv("image")  # encoding might be an issue here
        image = Image.open(io.BytesIO(image_data)) if image_data else None
        return image


    async def get_version(self):
        version = await self.kv_store.get_kv("version")
        return version


    async def get_last_update(self):
        last_update = await self.kv_store.get_kv("last_update")
        last_update_at = datetime.datetime.fromisoformat(last_update) if last_update else None
        return last_update_at


    async def get_next_client_update_at(self):
        next_client_update = await self.kv_store.get_kv("next_client_update")
        next_client_update_at = datetime.datetime.fromisoformat(next_client_update) if next_client_update else None
        return next_client_update_at


    async def get_image_buffer(self):
        image = await self.get_image()
        if image is None:
            return None
        output = io.BytesIO()
        image.save(output, format="PNG", bits=self.settings.bits_per_pixel, compress_level=9)
        return output.getvalue()


    async def _create_image(self):
        # Draw widgets
        image = Image.new(mode="RGB", size=self.settings.size, color=0xFFFFFF)
        ctx = DrawingContext(image, global_settings.font_path, global_settings.icon_path, self.settings.colors[0])
        for w in self.widgets:
            await w.draw(ctx)
            r = (w.settings.position[0], w.settings.position[1], w.settings.position[0]+w.settings.size[0]-1, w.settings.position[1]+w.settings.size[1]-1)
            if self.debug:
                ctx.draw.rectangle(r, outline=ctx.FOREGROUND)

        # for widget in self.widgets:
        #     # Create image
        #     widget_image = Image.new(mode="RGB", size=widget.size, color=0xFFFFFF)
        #     ctx = DrawingContext(widget_image)
        #     widget.draw(ctx)
        #     # Paste image into the main image
        #     image.paste(widget_image, widget.position)

        # Convert image with the right palette
        pal_img = Image.new("P", (1, 1))
        pal_img.putpalette([0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 0] * 64)

        return image.rotate(self.settings.rotation, expand=True).quantize(palette=pal_img)
        # return image.quantize(colors=3, palette=[0, 0, 0, 255, 255, 255, 255, 0, 0])


    def _image_is_different(self, current_image, new_image):
        if current_image is None:
            return True
        return ImageChops.difference(current_image, new_image).getbbox() is not None


    async def _update(self):
        logger.debug(f"Updating display {self.id}")
        now = datetime.datetime.now(datetime.timezone.utc)
        data = {
            "last_update": now.isoformat(), 
            "next_client_update": (now + self.update_interval + self.client_update_delay).isoformat()
        }

        current_image = await self.get_image()
        new_image = await self._create_image()
        is_different = self._image_is_different(current_image, new_image)
        if is_different:
            new_version = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
            output = io.BytesIO()
            new_image.save(output, format='PNG', bits=self.settings.bits_per_pixel, compress_level=9)
            output.seek(0, 0)
            data.update({
                "image": output.getvalue(), 
                "version": new_version,
            })
            logger.info(f"Display {self.id} updated to version {new_version}")
        else:
            current_version = await self.get_version()
            logger.info(f"Display {self.id}: still at version {current_version}")
        await self.kv_store.set_kv_from_dict(data)


    async def update_if_needed(self):
        last_update = await self.kv_store.get_kv("last_update")
        last_update_at = datetime.datetime.fromisoformat(last_update) if last_update else None

        update_needed = last_update_at is None or self.update_interval is None or self.settings.update_interval_s <= 0
        if not update_needed:
            now = datetime.datetime.now(datetime.timezone.utc)
            update_needed = (now - last_update_at) >= self.update_interval
        if update_needed:
            await self._update()
