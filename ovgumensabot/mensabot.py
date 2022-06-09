import asyncio
from datetime import datetime, timedelta, date

import pytz
from markdown import markdown
from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.errors import MForbidden
from mautrix.types import TextMessageEventContent, MessageType, Format, RelatesTo, RelationType, RoomID

from .db import MenuDatabase
from .menu import Menu
from .parser import get_menus, parse_movies

URLS = [
    'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-unicampus/speiseplan-unten/',
    'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-unicampus/speiseplan-oben/'
    # 'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-stendal/speiseplan/',
    # 'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-herrenkrug/speiseplan/',
    # 'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-kellercafe/speiseplan/'
]
NOTIF_TIME = {
    "h": 14,
    "m": 30
}
TZ = pytz.timezone('Europe/Berlin')


def date_keyword_to_date(date_keyword) -> date:
    switcher = {
        "today": date.today(),
        "tomorrow": date.today() + timedelta(days=1),
        "monday": date.today() + timedelta(days=-date.today().weekday(), weeks=1),
        "tuesday": date.today() + timedelta(days=1 - date.today().weekday(), weeks=1),
        "wednesday": date.today() + timedelta(days=2 - date.today().weekday(), weeks=1),
        "thursday": date.today() + timedelta(days=3 - date.today().weekday(), weeks=1),
        "friday": date.today() + timedelta(days=4 - date.today().weekday(), weeks=1)
    }
    return switcher.get(date_keyword)


def formatted_movie_list(movies: list[tuple[datetime, str]]) -> str:
    ret = "Next movies: \n\n"
    for movie in movies:
        datetime_str = movie[0].strftime("%d.%m.%Y, %H:%M")
        ret += f"* {datetime_str}: {movie[1]}\n"
    return ret


class MensaBot(Plugin):
    db: MenuDatabase
    loop_task: asyncio.Future

    async def start(self) -> None:
        self.db = MenuDatabase(self.database)
        self.loop_task = asyncio.ensure_future(self.fetch_loop(), loop=self.loop)

    async def stop(self) -> None:
        self.loop_task.cancel()

    async def fetch_loop(self) -> None:
        try:
            self.log.debug("Fetching loop started")
            while True:
                now = datetime.now(TZ)
                days = 1 if now > now.replace(hour=NOTIF_TIME.get("h"), minute=NOTIF_TIME.get("m"), second=0,
                                              microsecond=0) else 0
                scheduled_time = now.replace(hour=NOTIF_TIME.get("h"), minute=NOTIF_TIME.get("m"), second=0,
                                             microsecond=0) + timedelta(days=days)
                self.log.info(f"Scheduled fetch for {scheduled_time} in {scheduled_time - now} seconds")
                await asyncio.sleep((scheduled_time - now).total_seconds())
                asyncio.create_task(self.autofetch_menus())
        except asyncio.CancelledError:
            self.log.debug("Fetching loop stopped")
        except Exception:
            self.log.exception("Exception in fetching loop")

    @command.new("hunger", help="Show the meals")
    @command.argument("message", pass_raw=True, required=False)
    async def hunger_handler(self, evt: MessageEvent, message: str = "") -> None:
        new_menu = False
        if "fetch" in message:
            new_menu = await self.fetch_menus()
            message = message.replace('fetch', '').strip()
        date_keywords = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday"]
        if any(x in message.strip() for x in date_keywords):
            menus = self.db.get_menu_on_day(date_keyword_to_date(message))
        elif message == "":
            menus = self.db.get_menu_on_day(self.get_next_available_day())
        else:
            try:
                parsed_date: datetime.date = datetime.strptime(message.strip(), "%d.%m.%Y").date()
                menus = self.db.get_menu_on_day(parsed_date)
            except Exception:
                content = TextMessageEventContent(
                    msgtype=MessageType.NOTICE, format=Format.HTML,
                    body=f"There was an error parsing your date. ({message}) Expected format: dd.mm.yyyy",
                    formatted_body=markdown(f"There was an error parsing your date. (*{message}*)"
                                            f"<br>Expected format: `dd.mm.yyyy`"
                                            f"<br>"
                                            f"<br>You can also use keywords like `today`, `tomorrow`, `monday`,"
                                            f"`tuesday`, etc."),
                    relates_to=RelatesTo(
                        rel_type=RelationType("com.valentinriess.mensa"),
                        event_id=evt.event_id,
                    ))
                await evt.respond(content)
                return

        run = False
        for menu in menus:
            run = True
            if new_menu:
                await self.notify_subscribers(menu=menu)
                # do not send message twice if a subscriber triggered hunger and there is a new menu
                if not self.db.subscription_exists(room_id=evt.room_id):
                    await self.post_menu(room_id=evt.room_id, menu=menu)
            else:
                await self.post_menu(room_id=evt.room_id, menu=menu)
        if not run:
            content = TextMessageEventContent(
                msgtype=MessageType.NOTICE, format=Format.HTML,
                body=f"No meal for {message} :/",
                formatted_body=markdown(f"No meal for **{message}** :/"),
                relates_to=RelatesTo(
                    rel_type=RelationType("com.valentinriess.mensa"),
                    event_id=evt.event_id,
                ))
            await evt.respond(content)

    @command.new("subscribe", help="Get notified every day with the menu")
    async def subscribe(self, evt: MessageEvent) -> None:
        if self.db.subscription_exists(evt.room_id):
            content = TextMessageEventContent(
                msgtype=MessageType.NOTICE, format=Format.HTML,
                body="Your subscription is already active. Nothing to do here.",
                formatted_body=markdown("Your subscription is **already active**. Nothing to do here."),
                relates_to=RelatesTo(
                    rel_type=RelationType("com.valentinriess.mensa"),
                    event_id=evt.event_id,
                ))
            await evt.respond(content)
        else:
            self.db.insert_subscription(evt.room_id)
            content = TextMessageEventContent(
                msgtype=MessageType.NOTICE, format=Format.HTML,
                body=f"Enjoy your meal! Use !unsubscribe to end your subscription. Notifications can be expected "
                     f"every day at {NOTIF_TIME.get('h')}:{NOTIF_TIME.get('m')}.",
                formatted_body=markdown("Enjoy your meal! Use `!unsubscribe` to end your subscription."
                                        "<br><br>Notifications can be expected "
                                        f"every day at **{NOTIF_TIME.get('h')}:{NOTIF_TIME.get('m')}**."
                                        ),
                relates_to=RelatesTo(
                    rel_type=RelationType("com.valentinriess.mensa"),
                    event_id=evt.event_id,
                ))
            await evt.respond(content)

    @command.new("unsubscribe", help="End your daily subscription.")
    async def unsubscribe(self, evt: MessageEvent) -> None:
        if not self.db.subscription_exists(evt.room_id):
            content = TextMessageEventContent(
                msgtype=MessageType.NOTICE, format=Format.HTML,
                body="You have no active subscription. Nothing to do here.",
                formatted_body=markdown("You have **no active subscription**. Nothing to do here."),
                relates_to=RelatesTo(
                    rel_type=RelationType("com.valentinriess.mensa"),
                    event_id=evt.event_id,
                ))
            await evt.respond(content)
        else:
            self.db.delete_subscription(evt.room_id)
            content = TextMessageEventContent(
                msgtype=MessageType.NOTICE, format=Format.HTML,
                body="Your subscription has been cancelled.",
                formatted_body=markdown("Your subscription has been **cancelled**."),
                relates_to=RelatesTo(
                    rel_type=RelationType("com.valentinriess.mensa"),
                    event_id=evt.event_id,
                ))
            await evt.respond(content)

    @command.new("hid", help="Next Hörsaal im Dunkeln event")
    async def hid(self, evt: MessageEvent) -> None:
        movies = await parse_movies(self, "https://www.unifilm.de/studentenkinos/MD_HiD")

        # remove all old movies
        movies[:] = [movie for movie in movies if movie[0].date() >= datetime.now(TZ).date()]

        self.log.debug(f"Upcoming movies: {movies}")
        if len(movies) == 0:
            await evt.respond("No planned movies.")
            return
        else:
            # only keep movies of the next movie day
            next_movie_day = movies[0][0].date()
            movies[:] = [movie for movie in movies if movie[0].date() == next_movie_day]

        self.log.info(f"Movies on next movie day: {movies}")
        await evt.respond(formatted_movie_list(movies))

    async def fetch_menus(self) -> None:
        days = []
        for url in URLS:
            menus = await get_menus(mensabot=self, url=url)
            for menu in menus:
                if menu.day in days:
                    self.db.add_meals_to_menu(menu)
                else:
                    self.db.upsert_menu(menu)
                    days.append(menu.day)

    async def autofetch_menus(self):
        self.log.info("Autofetching...")
        if self.db.subscriptions_not_empty():
            await self.fetch_menus()
            if self.get_next_available_day() == date.today() + timedelta(days=1):
                for menu in self.db.get_menu_on_day(self.get_next_available_day()):
                    await self.notify_subscribers(menu)

    async def notify_subscribers(self, menu: Menu):
        if self.db.subscriptions_not_empty():
            for room_id in self.db.get_subscriptions():
                self.log.info(f"Send menu update to room_id {room_id}")
                await self.post_menu(room_id=room_id, menu=menu)

    async def post_menu(self, room_id: str, menu: Menu) -> bool:
        content = TextMessageEventContent(
            msgtype=MessageType.NOTICE, format=Format.HTML,
            body=f"{menu}",
            formatted_body=f"{menu.to_html()}")
        content["menu"] = menu.to_dict()
        try:
            await self.client.send_message(RoomID(room_id), content)
        except MForbidden:
            self.log.error("Wrong Room ID")
            return False
        return True

    def get_next_available_day(self):
        today = date.today()
        today2pm = datetime.now(TZ).replace(hour=14, minute=0, second=0, microsecond=0)
        days = self.db.get_menu_days()
        for day in days:
            if day >= today:
                if day != today:  # no menu today, returning the next available
                    return day
                elif datetime.now(TZ) > today2pm:
                    return days.__next__()
