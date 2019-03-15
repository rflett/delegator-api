from app import db
from app.Models import Organisation  # noqa
from sqlalchemy import String, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship


class TaskType(db.Model):
    __tablename__ = "task_types"

    id = Column('id', Integer(), primary_key=True)
    type = Column('type', String())
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
