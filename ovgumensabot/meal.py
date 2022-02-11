from typing import List, Dict


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
