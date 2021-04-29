from pytz import timezone
from babel.dates import format_date
from datetime import datetime
from loguru import logger
from .base import BaseWidget


class DateWidget(BaseWidget):

    def __init__(self, redis, id, config, datasource):
        super().__init__(redis, id, config, datasource)
        self.timezone = timezone(config['timezone'])
        self.date_format = config['date_format']


    async def draw(self, ctx):
        await super().draw(ctx)
        font = ctx.get_font(self.font[0], self.font[1])
        now = datetime.now(self.timezone)
        text = format_date(now, self.date_format, locale=self.locale)
        position = ( self.size[0]/2, self.size[1]/2 )
        ctx.draw_text_centered_xy(position, text, font=font, fill=tuple(self.colors[1]))
