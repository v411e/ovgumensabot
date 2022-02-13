import logging
from datetime import datetime
from typing import List

import pytz
from bs4 import BeautifulSoup
from maubot import Plugin

from .meal import Meal
from .menu import Menu
TZ = pytz.timezone('Europe/Berlin')


async def get_menus(mensabot: Plugin, url: str) -> List:
    async with mensabot.http.get(url) as resp:
        page = await resp.text()
    mensabot.log.debug(page)
    soup = BeautifulSoup(page, 'html.parser')
    div_mensa = soup.find_all("div", class_="mensa")

    if div_mensa:
        menu_tables = div_mensa[0].find_all("table")
    else:
        return []

    menus = []
    for menu_table in menu_tables:
        mensabot.log.debug(f"mensa_table {menu_table}")
        menus.append(parse_table(menu_table))
    return menus


def parse_table(menu_table) -> Menu:
    date_string = menu_table.find("thead").find("tr").find("td").string.split(',')[1].strip()
    day = datetime.strptime(date_string, "%d.%m.%Y").date()
    meals = []
    for meal_element in menu_table.find("tbody").find_all("tr"):
        meal = Meal(name=meal_element.find_all("td").pop(0).find("strong").contents.pop(0).string,
                    price=meal_element.find_all("td").pop(0).contents.pop(2).string)
        meals.append(meal)
    menu: Menu = Menu(day=day,
                      last_updated=datetime.now(TZ),
                      meals=meals)
    return menu
