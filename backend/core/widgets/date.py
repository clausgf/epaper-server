from typing import Literal, Optional
from pytz import timezone
from babel.dates import format_date, get_timezone
from datetime import datetime
from loguru import logger
from ..settings import global_settings
from ..datasources.base import BaseDatasource
from ..drawingcontext import DrawingContext
from .base import BaseWidget, BaseWidgetSettings


class DateWidgetSettings(BaseWidgetSettings):
    widget_class: Literal['DateWidget']
    date_format: Optional[str] = None


class DateWidget(BaseWidget):

    def __init__(self, id: str, settings: DateWidgetSettings, datasource: Optional[BaseDatasource] = None):
        super().__init__(id, settings, datasource)
        self.timezone = get_timezone(global_settings.timezone)

    async def draw(self, ctx: DrawingContext):
        await super().draw(ctx)
        font = ctx.get_font(self.settings.font[0], self.settings.font[1])
        now = datetime.now(self.timezone)
        text = format_date(now, self.settings.date_format or global_settings.date_format, locale=global_settings.locale)
        position = ( self.settings.size[0]/2, self.settings.size[1]/2 )
        ctx.draw_text_centered_xy(position, text, font=font, fill=tuple(self.settings.colors[1]))

