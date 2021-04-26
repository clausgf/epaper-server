from PIL import Image, ImageChops, ImagePalette
import random
import string
import datetime
import time
import io
import os
from loguru import logger

from . import widgets
from .drawingcontext import DrawingContext
from .utils import BaseRedis


class Display(BaseRedis):

    def __init__(self, redis_pool, id, default_settings, config, datasources):

        def get_config(key, default):
            return config.get(key, default_settings.get(key, default))

        super().__init__(redis_pool=redis_pool, base_key="display", id=id)
        self.aliases   = []
        self.config    = config
        self.size      = tuple(config["size"])
        self.bits_per_pixel = config["bits_per_pixel"]
        self.colors    = config["colors"]
        self.update_interval     = datetime.timedelta(seconds=get_config("update_interval", 3600))
        self.client_update_delay = datetime.timedelta(seconds=get_config("client_update_delay", 30))
        self.rotation  = get_config("rotation", 0)
        self.debug     = get_config("debug", False)
        self.font_path = get_config("font_path", "resources/fonts")
        self.icon_path = get_config("icon_path", "resources/icons")

        # create widgets
        self.widgets = []
        for id, widget_config in enumerate(config["widgets"]):
            widget_class = getattr(widgets, widget_config["class"] + "Widget")
            _config      = {**default_settings, 'colors': self.colors, **widget_config}
            _datasource  = datasources.get(widget_config.get('datasource'))
            widget_obj   = widget_class(redis_pool, id, _config, _datasource)
            self.widgets.append(widget_obj)


    async def get_image(self):
        image_data = await self.get_redis("image")
        image = Image.open(io.BytesIO(image_data)) if image_data else None
        return image


    async def get_version(self):
        version = await self.get_redis("version", encoding='utf-8')
        return version


    async def get_last_update(self):
        last_update = await self.get_redis("last_update", encoding='utf-8')
        last_update_at = datetime.datetime.fromisoformat(last_update) if last_update else None
        return last_update_at


    async def get_next_client_update(self):
        next_client_update = await self.get_redis("next_client_update", encoding='utf-8')
        next_client_update_at = datetime.datetime.fromisoformat(next_client_update) if next_client_update else None
        return next_client_update_at


    async def get_image_buffer(self):
        image = await self.get_image()
        if image is None:
            return None
        output = io.BytesIO()
        image.save(output, format="PNG", bits=self.bits_per_pixel, compress_level=9)
        return output.getvalue()


    async def _create_image(self):
        # Draw widgets
        image = Image.new(mode="RGB", size=self.size, color=0xFFFFFF)
        ctx = DrawingContext(image, self.font_path, self.icon_path, self.colors[0])
        for widget in self.widgets:
            await widget.draw(ctx)
            r = (widget.position[0], widget.position[1], widget.position[0]+widget.size[0]-1, widget.position[1]+widget.size[1]-1)
            #if hasattr(widget, 'colors'):
            #    ctx.draw.rectangle(r, outline=tuple(widget.colors[0]), fill=tuple(widget.colors[0]))
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

        return image.rotate(self.rotation, expand=True).quantize(palette=pal_img)
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
            new_image.save(output, format='PNG', bits=self.bits_per_pixel, compress_level=9)
            output.seek(0, 0)
            data.update({
                "image": output.getvalue(), 
                "version": new_version,
            })
            logger.info(f"Display {self.id} updated to version {new_version}")
        else:
            current_version = await self.get_version()
            logger.info(f"Display {self.id}: still at version {current_version}")
        await self.set_redis(data)


    async def update_if_needed(self):
        last_update = await self.get_redis("last_update", encoding='utf-8')
        last_update_at = datetime.datetime.fromisoformat(last_update) if last_update else None

        update_needed = last_update_at is None or self.update_interval is None
        if not update_needed:
            now = datetime.datetime.now(datetime.timezone.utc)
            update_needed = (now - last_update_at) >= self.update_interval
        if update_needed:
            await self._update()
