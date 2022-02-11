import asyncio
from datetime import datetime, timedelta

import pytz
from markdown import markdown
from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.errors import MForbidden
from mautrix.types import TextMessageEventContent, MessageType, Format, RelatesTo, RelationType, RoomID

from .db import MenuDatabase
from .menu import Menu

URL = 'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-unicampus/'


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
                now = datetime.now(tz=pytz.UTC)
                next_hour = (now + timedelta(hours=1)).replace(minute=42, second=0, microsecond=0)
                # next_hour = (now + timedelta(seconds=60))
                await asyncio.sleep((next_hour - now).total_seconds())
                asyncio.create_task(self.autofetch_menus())
        except asyncio.CancelledError:
            self.log.debug("Fetching loop stopped")
        except Exception:
            self.log.exception("Exception in fetching loop")

    @command.new("hunger", help="Show the meals")
    @command.argument("message", pass_raw=True, required=False)
    async def hunger_handler(self, evt: MessageEvent, message: str = "") -> None:
        new_menu = await self.fetch_menus()
        if "today" in message:
            menus = self.db.get_menu_on_days(f"%{datetime.strftime(datetime.now(), '%d.%m.%Y')}%")
        elif message == "":
            menus = self.db.get_latest_menu()
        else:
            menus = self.db.get_menu_on_days(f"%{message}%")

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
                body="Enjoy your meal! Use !unsubscribe to end your subscription.",
                formatted_body=markdown("Enjoy your meal! Use `!unsubscribe` to end your subscription."),
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

    async def fetch_menus(self) -> bool:
        menu: Menu = Menu()
        await menu.init(self, URL)
        return self.db.upsert_menu(menu)

    async def autofetch_menus(self):
        if self.db.subscriptions_not_empty() and await self.fetch_menus():
            for menu in self.db.get_latest_menu():
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
