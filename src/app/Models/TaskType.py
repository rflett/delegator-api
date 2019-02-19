from app import DBBase
from app.Models import Organisation  # noqa
from sqlalchemy import String, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship


class TaskType(DBBase):
    __tablename__ = "task_types"

    type = Column('type', String(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))

    orgs = relationship("Organisation")

    def __init__(self, type: str, org_id: int):
        self.type = type
        self.org_id = org_id

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TasktType object
        """
        return {
            "type": self.type,
            "org_id": self.org_id
        }
