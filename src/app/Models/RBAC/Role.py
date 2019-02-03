import datetime
from app import DBBase
from sqlalchemy import Column, String, DateTime


class Role(DBBase):
    __tablename__ = "rbac_roles"

    id = Column('id', String(), primary_key=True)
    name = Column('name', String())
    description = Column('description', String(), default=None)
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            id: str,
            name: str,
            description: str
    ):
        self.id = id
        self.name = name
        self.description = description

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Role object
        """
        return {
            "id":  self.id,
            "name": self.name,
            "description": self.description
        }
