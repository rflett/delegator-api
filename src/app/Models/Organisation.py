from app import DBBase
from sqlalchemy import Column, String, Integer


class Organisation(DBBase):
    __tablename__ = "organisations"

    id = Column('id', Integer(), primary_key=True)
    name = Column('name', String())

    def __init__(self, name: str):
        self.name = name

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }
