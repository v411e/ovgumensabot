from typing import List, Dict
from bs4 import BeautifulSoup
from mautrix.types import TextMessageEventContent, MessageType, Format, RelatesTo, RelationType
from maubot import Plugin, MessageEvent
from maubot.handlers import command

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


class Meal:
    """This class represents a meal"""
    name: str = ""
    price: str = ""

    def __init__(self, name: str, price: str):
        self.name = name
        self.price = price


    def __str__(self) -> str:
        return self.name + "\n" + self.price


    def to_list(self) -> List:
        return [self.name, self.price]


    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "price": self.price
        }


class Menu:
    """This class represents a menu (a list of meals)"""
    day: str = ""
    meals: List[Meal] = []

    async def init(self, mensabot: Plugin, url: str) -> None:
        self.meals = []
        async with mensabot.http.get(url) as resp:
            page = await resp.text()
        mensabot.log.info(page)
        soup = BeautifulSoup(page, 'html.parser')
        div_mensa = soup.find_all("div", class_="mensa")
        self.day = div_mensa[0].find("table").find("thead").find("tr").find("td").string
        for mensa_table in div_mensa:
            for element in mensa_table.find("table").find("tbody").find_all("tr"):
                meal = Meal(element.find_all("td").pop(0).find("strong").contents.pop(0).string,
                            element.find_all("td").pop(0).contents.pop(2).string)
                self.meals.append(meal)


    def __str__(self) -> str:
        plain_text = ""
        for meal in self.meals:
            plain_text += "\n----------\n" + str(meal)
        return f'Speiseplan für {self.day}:{plain_text}'


    def to_html(self) -> str:
        plain_text = ""
        for meal in self.meals:
            plain_text += "<hr><br><strong>" + meal.name + "</strong><br>" + meal.price
        return f'<h3>Speiseplan für {self.day}:</h3>{plain_text}'


    def to_list(self) -> List[List]:
        result = []
        for meal in self.meals:
            result.append(meal.to_list())
        return result


    def to_dict(self) -> Dict:
        result = {}
        for i in range(len(self.meals)):
            result[f'meal {i}'] = self.meals.__getitem__(i).to_dict()
        return result


if __name__ == '__main__':
    print(Menu(URL))
