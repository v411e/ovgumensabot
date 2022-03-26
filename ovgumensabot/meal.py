from typing import List, Dict
from attr import dataclass


@dataclass
class Meal:
    """This class represents a meal"""
    menu_day: str = None
    name: str = ""
    price: str = ""

    def __str__(self) -> str:
        return self.name + "\n" + self.price

    def to_list(self) -> List:
        return [self.name, self.price]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "price": self.price
        }
