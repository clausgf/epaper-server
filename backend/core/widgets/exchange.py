from pytz import timezone
from babel.dates import format_date
from datetime import datetime
from loguru import logger
from .base import BaseWidget

import datetime
from babel.dates import format_date, format_time, format_datetime
from exchangelib import DELEGATE, IMPERSONATION, Account, Credentials


class ExchangeCalendarWidget(BaseWidget):

    def __init__(self, redis, id, config, datasource):
        super().__init__(redis, id, config, datasource)
        self.timezone = timezone(config['timezone'])
        self.date_format = config['date_format']
        self.date_font = self.config.get('datefont', self.font)
        self.date_colors = self.config.get('datefont', self.colors)


    async def draw(self, ctx):
        await super().draw(ctx)
        item_font   = ctx.get_font(self.font[0], self.font[1])
        item_height = self.font[1] + 2
        date_font   = ctx.get_font(self.date_font[0], self.date_font[1])
        date_height = self.date_font[1]

        # get the data from the exchange server
        logger.info("Retrieving Exchange calendar")
        if not self.config.get('username') or not self.config.get('password') or not self.config.get('smtp_address'):
            logger.error("Exchange username/password not configured")
            return
        credentials = Credentials(username=self.config['username'], password=self.config['password'])
        account = Account(primary_smtp_address=self.config['smtp_address'], credentials=credentials, autodiscover=True, access_type=DELEGATE)

        start = datetime.datetime.now(tz=account.default_timezone)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        items = account.calendar.view(
            start=start,
            end=start + datetime.timedelta(days=7),
        ).order_by("start")

        y = 0
        last_date = None
        for item in items:
            # get start, end, subject and location as strings
            is_full_day = (not hasattr(item.start, 'time')) or (not item.start.time())
            if is_full_day:
                start_dt = item.start
                end_dt = item.end
                start_date = start_dt
                start_time = None
                end_time = None
                is_today = ( start_dt == datetime.datetime.now(tz=self.timezone).date() )
            else:
                start_dt = item.start.astimezone(self.timezone)
                end_dt = item.end.astimezone(self.timezone)
                start_date = start_dt.date()
                start_time = format_time(start_dt, format='short', locale=self.locale)
                end_time = format_time(end_dt, format='short', locale=self.locale)
                is_today = ( start_dt.date() == datetime.datetime.now(tz=self.timezone).date() )
            #date = format_date(start_dt, format='short', locale=self.locale)
            subject = ( item.subject if item.subject else "???") + ( f" ({item.location})" if item.location else "" )
            #logger.info(f"{day} {start_time}-{end_time} {subject} full_day={is_full_day} color={color}")

            # on a new day, place the day header
            while start_date != last_date:
                if last_date:
                    last_date = last_date + datetime.timedelta(days=1)
                else:
                    last_date = start_date
                day = format_datetime(last_date, self.date_format, locale=self.locale, tzinfo=self.timezone)
                is_highlighted = ( last_date.weekday() == 6 )

                y += int(item_height/2)
                if y + date_height < self.size[1]:
                    date_color = self.date_colors[2] if is_highlighted else self.date_colors[1]
                    ctx.draw_line ( ((0, y), (self.size[0]-1, y)), width=1, fill=tuple(date_color) )
                    # todo: fill background
                    ctx.draw_text_xy ( ( 0, y+1 ), f"{day}", font=date_font, fill=tuple(date_color) )
                    y += int(date_height)
                    y += int(item_height/3)
                    ctx.draw_line ( ((0, y-2), (self.size[0]-1, y-2)), width=1, fill=tuple(date_color) )

            # draw time and subject of the calendar event
            if y < self.size[1]:
                color = self.colors[2] if is_highlighted else self.colors[1]
                if not is_full_day:
                    ctx.draw_text_xy( ( 0, y ), f"{start_time}-{end_time}", font=item_font, fill=tuple(color) )
                x = ctx.textsize("XX:XX-XX:XX ", item_font)[0]
                ctx.draw_text_xy( ( 0+x, y ), f"{subject}", font=item_font, fill=tuple(color) )
                y += item_height
