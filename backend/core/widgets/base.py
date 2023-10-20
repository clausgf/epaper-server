from pydantic import BaseModel
from typing import Optional, Tuple, List, Literal
from loguru import logger
from ..settings import global_settings
from ..datasources.base import BaseDatasource
from ..drawingcontext import DrawingContext


class BaseWidgetSettings(BaseModel):
    widget_class: Literal['BaseWidget']
    position: Tuple[int, int]
    size: Tuple[int, int]
    colors: Optional[List[Tuple[int, int, int]]] = None   # guarateed to be set by Epaper class
    font: Optional[Tuple[str, int]] = None                # guarateed to be set by Epaper class
    datasource: Optional[str] = None


class BaseWidget:

    def __init__(self, id: str, settings: BaseWidgetSettings, datasource: Optional[BaseDatasource] = None):
        self.id = id
        self.settings = settings
        self.datasource = datasource
        self.init_background = True
    
    async def draw(self, ctx: DrawingContext):
        """Draws the widget using the given drawing context (which is attached to an image) using the datasource."""
        logger.debug(f"Drawing widget type {self.settings.widget_class}::{self.id}@{self.settings.position} size {self.settings.size}")
        ctx.origin = self.settings.position
        p0 = self.settings.position
        p1 = tuple(sum(x)-1 for x in zip(self.settings.position, self.settings.size))
        ctx.draw.rectangle([p0, p1], fill=tuple(self.settings.colors[0]))
        #ctx.draw.rectangle([p0, p1], outline=(255,0,0))
