import os
import math
from loguru import logger

from PIL import Image, ImageFont, ImageDraw, ImageColor


class FontProvider:
    cache = {}

    def __init__(self, base_path):
        self.base_path = base_path

    def get(self, name, fontsize):
        # Load from cache
        font = self.cache.get((name, fontsize))
        if font is not None:
            return font

        # Create new font
        fontpath = os.path.join(self.base_path, name)
        font = ImageFont.truetype(fontpath, fontsize)
        self.cache[(name, fontsize)] = font

        return font


class IconProvider:
    cache = {}

    def __init__(self, base_path):
        self.base_path = base_path

    def get(self, name):
        image = IconProvider.cache.get(name)
        if image is not None:
            return image

        image = Image.open(os.path.join(self.base_path, name))
        IconProvider.cache[name] = image

        return image


class DrawingContext:
    FOREGROUND = (0, 0, 0)
    BACKGROUND = (255, 255, 255)
    COLOR = (255, 0, 0)

    def __init__(self, image, font_path, icon_path, bg_color):
        self.img = image
        self.draw = ImageDraw.Draw(image)
        self.font_provider = FontProvider(font_path)
        self.image_provider = IconProvider(icon_path)
        self.origin = (0,0)
        self.size = image.size
        self.draw.rectangle([(0,0), self.size], fill=tuple(bg_color))


    def get_font(self, name, size):
        return self.font_provider.get(name, size)


    def get_image(self, name):
        return self.image_provider.get(name)


    def draw_image_centered(self, xy, name):
        image = self.get_image(name)
        x = math.floor(self.origin[0] + xy[0] - image.width / 2)
        y = math.floor(self.origin[1] + xy[1] - image.height / 2)
        self.img.paste(image, (x, y))
        return image.size


    def draw_line(self, xys, *args, **params):
        xys = tuple( (self.origin[0] + xy[0], self.origin[1] + xy[1]) for xy in xys )
        self.draw.line( xys, *args, **params)


    def textsize(self, text, font):
        width, height = self.draw.textsize(text, font)
        return width, height


    def draw_text_centered_xy(self, xy, text, font, **params):
        width, height = self.draw.textsize(text, font)
        x,  y  = math.floor(xy[0] - width/2), math.floor(xy[1] - height/2)
        return self.draw_text_xy( (x, y), text, font, **params)


    def draw_text_xy(self, xy, text, font, **params):
        params['fill'] = params.get( 'fill', DrawingContext.FOREGROUND )
        x, y = self.origin[0] + xy[0], self.origin[1] + xy[1]

        width, height = self.draw.textsize(text, font)
        mask = Image.new("1", (width, height), color=0)
        draw = ImageDraw.Draw(mask)
        draw.text((0, 0), text, font=font, fill=1)
        image = Image.new(self.img.mode, (width, height), color=params['fill'])
        self.img.paste(image, (x,y), mask=mask)
        #f = params['fill']
        #print(f"xy={xy}  text={text}  fill={f}")

        #self.draw.text((x, y), text, font=font, **params)
        return width, height
