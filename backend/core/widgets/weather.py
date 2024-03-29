"""Weather Widget

The drawing code in this widget is heavily based on https://github.com/ugomeda/esp32-epaper-display
"""

from typing import Literal, Optional
import math
import pytz
from datetime import datetime, timedelta
from babel.dates import format_time, get_timezone
from loguru import logger
import matplotlib.pyplot as plt
import matplotlib.dates as md
import PIL
from ..settings import global_settings
from ..datasources.base import BaseDatasource
from ..drawingcontext import DrawingContext
from .base import BaseWidget, BaseWidgetSettings


WEATHER_CODES_TO_IMAGES = {
    "01d": "wi-day-sunny",
    "01n": "wi-moon-new",
    "02d": "wi-day-cloudy",
    "02n": "wi-night-cloudy",
    "03d": "wi-cloud",
    "03n": "wi-cloud",
    "04d": "wi-cloudy",
    "04n": "wi-cloudy",
    "09d": "wi-day-showers",
    "09n": "wi-night-showers",
    "10d": "wi-day-rain",
    "10n": "wi-night-rain",
    "11d": "wi-day-thunderstorm",
    "11n": "wi-night-thunderstorm",
    "13d": "wi-snow",
    "13n": "wi-snow",
    "50d": "wi-fog",
    "50n": "wi-fog",
}

BASE_URL = "https://api.openweathermap.org/data/2.5/"


fonts = {
    "main_temp": ("OpenSans-Bold-webfont.woff", 36),
    "details": ("OpenSans-Regular-webfont.woff", 22),
    "next": ("OpenSans-Regular-webfont.woff", 18),
    "next_bold": ("OpenSans-Bold-webfont.woff", 18),
}

def _get_font(ctx, section):
    f = fonts[section]
    return ctx.get_font(f[0], f[1])

##############################################################################

IMAGE_HEIGHT = 94

class WeatherNowWidgetSettings(BaseWidgetSettings):
    widget_class: Literal['WeatherNowWidget']
    datasource: str

class WeatherNowWidget(BaseWidget):

    def __init__(self, id: str, settings: WeatherNowWidgetSettings, datasource: Optional[BaseDatasource] = None):
        if datasource is None:
            raise ValueError("datasource must be set")
        super().__init__(id, settings, datasource)
        self.temperature_format = "{:.0f}°F" if global_settings.units == "imperial" else "{:.0f}°C"
        self.timezone = get_timezone(global_settings.timezone)

    def _wind_to_kn(self, speed):
        if global_settings.units == "imperial":
            return speed * 0.868976
        else:
            return speed * 1.94384

    async def draw(self, ctx: DrawingContext):
        await super().draw(ctx)
        data = await self.datasource.get_data()
        weather = data["current"]
        logger.debug(f"current weather: {weather}")

        # Icon (94x94)
        ctx.draw_image_centered( (IMAGE_HEIGHT / 2, IMAGE_HEIGHT / 2), f"weather/{WEATHER_CODES_TO_IMAGES[weather['weather'][0]['icon']]}.png" )

        # Temperature
        temperature_text = self.temperature_format.format(weather["temp"])
        w, _ = ctx.draw_text_xy( (IMAGE_HEIGHT, 6), temperature_text, font=_get_font(ctx, "main_temp") )
        w += 8

        # Precipitation
        #precipitation = self.datasource.now["rain"]["1h"] + self.datasource.now["snow"]["1h"]
        #precipitation_text = f"{precipitation} mm"
        #ctx.draw_text_xy( (IMAGE_HEIGHT + w + 15, 60), precipitation_text, font=_get_font(ctx, "details") )

        # Wind
        wind_direction = weather["wind_deg"]
        wind_speed = self._wind_to_kn( weather["wind_speed"] )
        wind_gust = self._wind_to_kn( weather.get("wind_gust", 0) )
        gust_str = f"G{wind_gust:.0f}" if wind_gust != 0 and wind_gust > 1.1*wind_speed else ""
        wind_text = f"{wind_direction}° {wind_speed:.0f}{gust_str} kn"
        ctx.draw_text_xy( (IMAGE_HEIGHT + w + 15, 20), wind_text, font=_get_font(ctx, "details") )

        # cloud cover
        ctx.draw_text_xy( (IMAGE_HEIGHT, 44), weather['weather'][0]["description"], font=_get_font(ctx, "details") )


##############################################################################

MIN_WIDTH = 80
SMALL_IMAGE_HEIGHT = 47

class WeatherForecastWidgetSettings(BaseWidgetSettings):
    widget_class: Literal['WeatherForecastWidget']
    datasource: str

class WeatherForecastWidget(BaseWidget):

    def __init__(self, id: str, settings: WeatherForecastWidgetSettings, datasource: Optional[BaseDatasource] = None):
        if datasource is None:
            raise ValueError("datasource must be set")
        super().__init__(id, settings, datasource)
        self.temperature_format = "{:.0f}°F" if global_settings.units == "imperial" else "{:.0f}°C"
        self.timezone = get_timezone(global_settings.timezone)

    async def draw(self, ctx: DrawingContext):
        await super().draw(ctx)
        # Display the weather for the rest of the day
        data = await self.datasource.get_data()
        items_count = math.floor(self.settings.size[0] / MIN_WIDTH)
        for i in range(0, items_count):
            x = i * self.settings.size[0] / items_count
            w = self.settings.size[0] / items_count

            weather = data["hourly"][3*(i+1)]
            logger.debug(f"hourly weather[{i}]: {weather}")

            # Icon (47x47)
            ctx.draw_image_centered( (x + w / 2, SMALL_IMAGE_HEIGHT / 2),
                f"weather_small/{WEATHER_CODES_TO_IMAGES[weather['weather'][0]['icon']]}.png" )

            # Temperature
            temperature = self.temperature_format.format(weather["temp"])
            ctx.draw_text_centered_xy(
                (x + w / 2, SMALL_IMAGE_HEIGHT + 5),
                temperature,
                _get_font(ctx, "next_bold"),
            )

            # Date
            date = datetime.fromtimestamp(weather["dt"], pytz.UTC) # OWM timestamps are in UTC
            ctx.draw_text_centered_xy(
                (x + w / 2, SMALL_IMAGE_HEIGHT + 25),
                format_time(
                    date, format="short", locale=(global_settings.locale.split("_")[0]), tzinfo=self.timezone
                ),
                _get_font(ctx, "next"),
            )

##############################################################################

class WeatherPrecipitationWidgetSettings(BaseWidgetSettings):
    widget_class: Literal['WeatherPrecipitationWidget']
    datasource: str

class WeatherPrecipitationWidget(BaseWidget):

    def __init__(self, id: str, settings: WeatherPrecipitationWidgetSettings, datasource: Optional[BaseDatasource] = None):
        if datasource is None:
            raise ValueError("datasource must be set")
        super().__init__(id, id, settings, datasource)
        self.timezone = get_timezone(global_settings.timezone)

    async def draw(self, ctx: DrawingContext):
        await super().draw(ctx)
        onecall = await self.datasource.get_data()
        precipitation = [(datetime.fromtimestamp(f['dt'], pytz.UTC).astimezone(self.timezone), f['precipitation']) for f in onecall['minutely']]
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(self.settings.size[0]/100.0, self.settings.size[1]/100.0), dpi=100)
        ax.set_ylim(0,10)
        ax.plot(*zip(*precipitation), 'k')
        ax.grid()
        ax.tick_params(direction='in')
        xfmt = md.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(xfmt)
        ax.set_xticks(ax.get_xticks()[::2])
        fig.tight_layout()
        fig.subplots_adjust(bottom=0.24)
        fig.canvas.draw()
        img = PIL.Image.frombytes('RGB', fig.canvas.get_width_height(),fig.canvas.tostring_rgb())
        ctx.img.paste(img, self.position)
        plt.close()

##############################################################################

class WeatherTemperatureWidgetSettings(BaseWidgetSettings):
    widget_class: Literal['WeatherTemperatureWidget']
    datasource: str

class WeatherTemperatureWidget(BaseWidget):
    def __init__(self, id: str, settings: WeatherTemperatureWidgetSettings, datasource: Optional[BaseDatasource] = None):
        if datasource is None:
            raise ValueError("datasource must be set")
        super().__init__(id, settings, datasource)
        self.timezone = get_timezone(global_settings.timezone)

    async def draw(self, ctx: DrawingContext):
        await super().draw(ctx)
        onecall = await self.datasource.get_data()
        temp = [(datetime.fromtimestamp(f['dt'], pytz.UTC).astimezone(self.timezone), f['temp']) for f in onecall['hourly']]
        pressure = [(datetime.fromtimestamp(f['dt'], pytz.UTC).astimezone(self.timezone), f['pressure']) for f in onecall['hourly']]
        humidity = [(datetime.fromtimestamp(f['dt'], pytz.UTC).astimezone(self.timezone), f['humidity']) for f in onecall['hourly']]
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(self.settings.size[0]/100.0, self.settings.size[1]/100.0), dpi=100)
        ax.set_ylim(-10,40)
        ax.plot(*zip(*temp), 'k')
        ax.grid()
        ax.tick_params(direction='in')
        xfmt = md.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(xfmt)
        ax.set_xticks(ax.get_xticks()[::2])
        fig.tight_layout()
        fig.subplots_adjust(bottom=0.24)
        fig.canvas.draw()
        img = PIL.Image.frombytes('RGB', fig.canvas.get_width_height(),fig.canvas.tostring_rgb())
        ctx.img.paste(img, self.settings.position)
        plt.close()
