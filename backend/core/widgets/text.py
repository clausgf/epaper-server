from typing import Literal, Optional
from loguru import logger
from ..settings import global_settings
from ..datasources.base import BaseDatasource
from ..drawingcontext import DrawingContext
from .base import BaseWidget, BaseWidgetSettings


class TextWidgetSettings(BaseWidgetSettings):
    widget_class: Literal['TextWidget']
    format: str


class TextWidget(BaseWidget):

    def __init__(self, id: str, settings: TextWidgetSettings, datasource: Optional[BaseDatasource] = None):
        super().__init__(id, settings, datasource)

    async def draw(self, ctx: DrawingContext):
        await super().draw(ctx)
        font = ctx.get_font(self.settings.font[0], self.settings.font[1])

        if self.datasource:
            data = await self.datasource.get_data()
            logger.debug(f"data: {data}")
            try:
                text = self.settings.format.format(**data)
            except KeyError as ex:
                logger.error(f"Key not found exception drawing widget {self.settings.widget_class}:{self.id}, datasource {self.datasource.id}: {ex}")
                text = "?"
        else:
            text = self.settings.format

        position = ( self.settings.size[0]/2, self.settings.size[1]/2 )
        ctx.draw_text_centered_xy(position, text, font=font, fill=tuple(self.settings.colors[1]))
