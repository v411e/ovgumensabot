import logging
from datetime import datetime
from typing import List, Dict

import pytz
from bs4 import BeautifulSoup
from maubot import Plugin

from .meal import Meal

from attr import dataclass


@dataclass
class Menu:
    """This class represents a menu (a list of meals)"""
    day: datetime.date = None
    last_updated: datetime = None
    meals: List[Meal] = []

    def __str__(self) -> str:
        plain_text = ""
        for meal in self.meals:
            plain_text += "\n----------\n" + str(meal)
        return f"Speiseplan für {self.day.strftime('%A, %d.%m.%Y')}:{plain_text}"

    def to_html(self) -> str:
        plain_text = ""
        for meal in self.meals:
            plain_text += "<hr><br><strong>" + meal.name + "</strong><br>" + meal.price
        return f"<h3>Speiseplan für {self.day.strftime('%A, %d.%m.%Y')}:</h3>{plain_text}"

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
