from app import DBBase
from sqlalchemy import Integer, Column, String


class Organisation(DBBase):
    __tablename__ = "organisations"

    id = Column('id', Integer())
    name = Column('name', String())

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
