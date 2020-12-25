from loguru import logger


class BaseWidget:

    def __init__(self, redis, id, config, datasource):
        self.id = id
        self.config = config
        self.datasource = datasource
        self.position = tuple(config["position"])
        self.size = tuple(config["size"])
        self.widget_class = config.get('class')

    async def draw(self, ctx):
        """Draws the widget using the given drawing context (which is attached to an image) using the datasource."""
        logger.debug(f"Drawing widget type {self.widget_class}::{self.id}@{self.position} size {self.size}")
        ctx.origin = self.position
