from loguru import logger


class BaseWidget:

    def __init__(self, redis, id, config, datasource):
        self.id = id
        self.config = config
        self.datasource = datasource
        self.position = tuple(config["position"])
        self.size = tuple(config["size"])
        self.widget_class = config.get('class')

        # defaults to be propagated to concrete widgets
        self.locale = config['locale']
        self.font = config['font']
        self.colors = config['colors']
        self.init_background = True


    async def draw(self, ctx):
        """Draws the widget using the given drawing context (which is attached to an image) using the datasource."""
        logger.debug(f"Drawing widget type {self.widget_class}::{self.id}@{self.position} size {self.size}")
        ctx.origin = self.position
        p0 = self.position
        p1 = tuple(sum(x) for x in zip(self.position, self.size))
        ctx.draw.rectangle([p0, p1], fill=tuple(self.colors[0]))
        #ctx.draw.rectangle([p0, p1], outline=(255,0,0))

