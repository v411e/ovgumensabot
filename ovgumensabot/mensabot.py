from bs4 import BeautifulSoup
from mautrix.types import TextMessageEventContent, MessageType, Format, RelatesTo, RelationType
from maubot import Plugin, MessageEvent
from maubot.handlers import command

from .menu import Menu

URL = 'https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-unicampus/'


class MensaBot(Plugin):

    @command.new("hunger", help="Show the meals")
    @command.argument("message", pass_raw=True, required=False)
    async def hunger_handler(self, evt: MessageEvent, message: str = "") -> None:
        menu: Menu = Menu()
        await menu.init(self, URL)
        content = TextMessageEventContent(
            msgtype=MessageType.NOTICE, format=Format.HTML,
            body=f"{menu}",
            formatted_body=f"{menu.to_html()}",
            relates_to=RelatesTo(
                rel_type=RelationType("com.valentinriess.mensa"),
                event_id=evt.event_id,
            ))
        content["menu"] = menu.to_dict()
        await evt.respond(content)


