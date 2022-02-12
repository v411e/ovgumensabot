import datetime
import logging
from typing import List, Generator

from sqlalchemy import (Column, String, DateTime, Date, ForeignKey, Table, MetaData,
                        select, func)
from sqlalchemy.engine.base import Engine

from ovgumensabot.meal import Meal
from ovgumensabot.menu import Menu


class MenuDatabase:
    menus: Table
    meals: Table
    subscriptions: Table
    db: Engine

    def __init__(self, db: Engine) -> None:
        self.db = db

        meta = MetaData()
        meta.bind = db

        self.menus = Table("menus", meta,
                           Column("day", Date, primary_key=True),
                           Column("last_updated", DateTime, nullable=False))

        self.meals = Table("meals", meta,
                           Column("menu_day", Date, ForeignKey("menus.day", ondelete="CASCADE", primary_key=True)),
                           Column("price", String(255), nullable=False),
                           Column("name", String(255), nullable=False))

        self.subscriptions = Table("subscriptions", meta,
                                   Column("room_id", String(255), primary_key=True))

        meta.create_all()

    def upsert_menu(self, menu: Menu) -> bool:
        logging.getLogger("maubot").info(f"Inserted menu from {menu.day} into database.")
        with self.db.begin() as tx:
            if self.menu_day_exists(menu):
                tx.execute(self.menus.update()
                           .where(self.menus.c.day == menu.day).values(day=menu.day, last_updated=menu.last_updated))
                tx.execute(self.meals.delete().where(self.meals.c.menu_day == menu.day))
                tx.execute(self.meals.insert(),
                           [{"menu_day": menu.day, "price": meal.price,
                             "name": meal.name}
                            for meal in menu.meals])
                return False  # menu was already existent
            else:
                tx.execute(self.menus.insert()
                           .values(day=menu.day, last_updated=menu.last_updated))
                tx.execute(self.meals.insert(),
                           [{"menu_day": menu.day, "price": meal.price,
                             "name": meal.name}
                            for meal in menu.meals])
                return True  # menu is new

    def subscriptions_not_empty(self) -> bool:
        rows = self.db.execute(select([func.count()]).select(self.subscriptions)).scalar()
        logging.getLogger("maubot").info(f"subscriptions not empty count {rows}")
        return rows and rows > 0

    def subscription_exists(self, room_id: str) -> bool:
        rows = self.db.execute(
            select([func.count()]).select(self.subscriptions).where(self.subscriptions.c.room_id == room_id)).scalar()
        logging.getLogger("maubot").info(f"subscription count {rows}")
        return rows and rows > 0

    def menu_day_exists(self, menu: Menu) -> bool:
        rows = self.db.execute(select([func.count()]).select(self.menus).where(self.menus.c.day == menu.day)).scalar()
        logging.getLogger("maubot").info(f"rows {rows}")
        return rows and rows > 0

    def get_menu_on_day(self, day: datetime.date) -> Generator:
        logging.getLogger("maubot").info(f"Search for day {day}")
        menu_rows = self.db.execute(select([self.menus]).where(self.menus.c.day.like(day)))
        return self._rows_to_menus(menu_rows)

    def get_latest_menu(self) -> Generator:
        menu_row = self.db.execute(select([self.menus]).order_by(self.menus.c.last_updated.desc()).limit(1))
        logging.getLogger("maubot").info(f"first menu_row {menu_row}")
        return self._rows_to_menus(menu_row)

    def _rows_to_menus(self, menu_rows) -> Generator:
        for menu_row in menu_rows:
            logging.getLogger("maubot").info(f"menu_row {menu_row}")
            meal_rows = self.db.execute(select([self.meals]).where(self.meals.c.menu_day == menu_row[0]))
            meals_of_the_day = []
            for meal_row in meal_rows:
                meals_of_the_day.append(Meal(menu_day=meal_row[0], price=meal_row[1], name=meal_row[2]))
            yield Menu(day=menu_row[0], last_updated=menu_row[1], meals=meals_of_the_day)

    def insert_subscription(self, room_id: str) -> None:
        self.db.execute(self.subscriptions.insert().values(room_id=room_id))

    def get_subscriptions(self) -> List:
        rows = self.db.execute(self.subscriptions.select())
        for row in rows:
            yield row[0]

    def delete_subscription(self, room_id: str) -> None:
        self.db.execute(self.subscriptions.delete().where(self.subscriptions.c.room_id == room_id))
