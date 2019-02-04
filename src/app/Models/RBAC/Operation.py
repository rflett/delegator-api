import datetime
from app import DBBase
from sqlalchemy import Column, String, DateTime


CREATE = 'CREATE'
DELETE = 'DELETE'
UPDATE = 'UPDATE'


class Operation(DBBase):
    __tablename__ = "rbac_operations"

    id = Column('id', String(), primary_key=True)
    name = Column('name', String(), nullable=False)
    description = Column('description', String())
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
        :return: The dict repr of an Operation object
        """
        return {
            "id":  self.id,
            "name": self.name,
            "description": self.description
        }
