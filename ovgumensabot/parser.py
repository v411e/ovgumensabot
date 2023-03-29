from datetime import datetime
from typing import List

import bs4.element
import pytz
from bs4 import BeautifulSoup
from maubot import Plugin

from .meal import Meal
from .menu import Menu

import urllib.request

TZ = pytz.timezone('Europe/Berlin')


def get_page() -> str:
    """Return website as html string.
    Used for debugging.
    
    """
    fp = urllib.request.urlopen(
        "https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-unicampus/speiseplan-unten/")
    mybytes = fp.read()

    page = mybytes.decode("utf8")
    fp.close()
    return page


def get_menus_from_page(page: str) -> List[Menu]:
    """Return a list of all menus from a given html source

    @param page: Html source string
    @return: List of menus
    """
    soup = BeautifulSoup(page, 'html.parser')
    div_mensa = soup.find_all("div", class_="mensa")

    if div_mensa:
        menu_tables = div_mensa[0].find_all("table")
    else:
        return []

    menus = []
    for menu_table in menu_tables:
        menus.append(parse_table(menu_table))
    return menus


async def get_menus(mensabot: Plugin, url: str) -> List[Menu]:
    """Wrapper of get_menus_from_page() for the maubot plugin.
    Loads webpage from url and returns a list of menus.

    @param mensabot: Mensabot maubot plugin
    @param url: URL string
    @return: List of menus
    """
    async with mensabot.http.get(url) as resp:
        page: str = await resp.text()
    return get_menus_from_page(page)


def parse_table(menu_table: bs4.element.Tag) -> Menu:
    """Returns a menu from a menu_table html-source.
    One menu includes several meals.

    @param menu_table: html-source object
    @return: Menu object
    """
    date_string = menu_table.find("thead").find("tr").find("td").string.split(',')[1].strip()
    day = datetime.strptime(date_string, "%d.%m.%Y").date()
    meals = []
    for meal_element in menu_table.find("tbody").find_all("tr"):
        cells = list(meal_element.children)
        # First cell contains name and price, second symbols, third for some reasons all other meals
        name_and_price = cells[0]
        symbols = None
        if len(cells) > 1:
            symbols = cells[1]
        try:
            if "Beilagen:" in name_and_price.text:
                name = name_and_price.text
                price = "-"
            else:

                # Price is everything else but the bold printed part
                price = name_and_price.text.replace(name_and_price.find("strong").text, "").strip()
                prices: List[str] = []
                # Tag prices with [ST]udierende, [MA]itarbeitende, [EX]terne
                for group_price, group in zip(price.split("|"), ["ST", "MA", "EX"]):
                    prices.append(f"{group}: {group_price.strip()}€")
                price = " / ".join(prices)

                # Remove english text (enclosed in <span class="grau">)
                name_and_price.find("span", {"class", "grau"}).decompose()
                # German name is everything else, that's bold and not removed
                name = name_and_price.find("strong").text
                if symbols is not None:
                    # Add symbols to name (vegetarian, vegan, ...)
                    symbol_additions = []
                    for symbol in symbols.find_all("img"):
                        # Get simple descriptive word from img title
                        symbol_title = symbol.get("title").replace("Symbol", "").strip()
                        # Symbol appears twice, so check if already noted
                        if symbol_title not in symbol_additions:
                            symbol_additions.append(symbol_title)
                    if symbol_additions:
                        name = f"{name} ({'/'.join(symbol_additions)})"
        except IndexError:
            print(f"IndexError on meal_element: {meal_element}")
            continue
        meal = Meal(name=name, price=price)
        meals.append(meal)

    menu: Menu = Menu(day=day,
                      last_updated=datetime.now(TZ),
                      meals=meals)
    return menu


async def parse_movies(mensabot: Plugin, url: str) -> list[tuple[datetime, str]]:
    """Parse hoersaal im dunkeln movie calendar → https://www.unifilm.de/studentenkinos/MD_HiD

    @param mensabot: Maubot plugin
    @param url: URL string
    @return: Tuples of datetime and str (date and movie-title)
    """
    async with mensabot.http.get(url) as resp:
        page = await resp.text()
    # mensabot.log.debug(page)
    soup = BeautifulSoup(page, "html.parser")

    # locate calendar for current semester
    div_semester = soup.find(
        "div", class_="kino-detail-spielplan spielplan-thisSemester")

    # locate all movies in current semester
    div_movie: List[BeautifulSoup] = div_semester.find_all(
        "div", class_="semester-film-row")

    movies_dict = {}

    # for each movie locate date, time and title
    for movie in div_movie:
        date = movie.find("div", class_="film-row-text film-row-datum").text
        time = movie.find("div", class_="film-row-text film-row-uhrzeit").text
        date_time_str = f"{date.strip().split(' ', 1)[1]}-{time.split(' ', 1)[0]}"
        parsed_datetime: datetime = datetime.strptime(
            date_time_str, "%d.%m.%Y-%H:%M")
        # ignore space at the end of each title
        title = movie.find(
            "div", class_="film-row-text film-row-titel").text.strip()

        movies_dict[parsed_datetime] = title

    return sorted(movies_dict.items())
