from datetime import datetime, timedelta
from typing import List, Dict

import pytz
from bs4 import BeautifulSoup
from maubot import Plugin

from .meal import Meal

from attr import dataclass


@dataclass
class Menu:
    """This class represents a menu (a list of meals)"""
    day: str = None
    last_updated: datetime = None
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
                meal = Meal(name=element.find_all("td").pop(0).find("strong").contents.pop(0).string,
                            price=element.find_all("td").pop(0).contents.pop(2).string)
                self.meals.append(meal)
        self.last_updated = datetime.now(tz=pytz.UTC)

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
