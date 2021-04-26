from pytz import timezone
from babel.dates import format_date
from datetime import datetime
from loguru import logger
from .base import BaseWidget


class TextWidget(BaseWidget):

    def __init__(self, redis, id, config, datasource):
        super().__init__(redis, id, config, datasource)
        self.format = config['format']


    async def draw(self, ctx):
        await super().draw(ctx)
        font = ctx.get_font(self.font[0], self.font[1])

        if self.datasource:
            data = await self.datasource.get_data()
            logger.debug(f"data: {data}")
            try:
                text = self.format.format(**data)
            except KeyError as ex:
                logger.error(f"Key not found exception drawing widget {self.widget_class}:{self.id}, datasource {self.datasource.id}: {ex}")
                text = "?"
        else:
            text = self.format

        position = ( self.size[0]/2, self.size[1]/2 )
        ctx.draw_text_centered_xy(position, text, font=font, fill=tuple(self.colors[1]))
