from datetime import datetime
from typing import List, Dict

from dataclasses import dataclass

from ovgumensabot.meal import Meal


class Menu:
    """This class represents a menu (a list of meals)"""
    day: datetime.date
    last_updated: datetime
    meals: List[Meal]

    def __init__(self, day: datetime.date = None, last_updated: datetime = None, meals: List[Meal] = []):
        self.day = day
        self.last_updated = last_updated
        self.meals = meals

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
