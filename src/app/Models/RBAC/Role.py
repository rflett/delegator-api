import datetime
from app import db
from sqlalchemy import Column, String, DateTime, Integer


class Role(db.Model):
    __tablename__ = "rbac_roles"

    id = Column('id', String(), primary_key=True)
    rank = Column('rank', Integer())
    name = Column('name', String())
    description = Column('description', String(), default=None)
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            id: str,
            rank: int,
            name: str,
            description: str
    ):
        self.id = id
        self.rank = rank
        self.name = name
        self.description = description

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Role object
        """
        return {
            "id":  self.id,
            "rank": self.rank,
            "name": self.name,
            "description": self.description
        }
