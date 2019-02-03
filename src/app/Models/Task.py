import datetime
from app import DBBase
from app.Models import Organisation, User  # noqa
from sqlalchemy import Integer, String, DateTime, Column, ForeignKey
from sqlalchemy.orm import relationship


class Task(DBBase):
    __tablename__ = "tasks"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    title = Column('title', String())
    description = Column('description', String())
    status = Column('status', String())
    assignee = Column('assignee', Integer(), ForeignKey('users.id'))
    created_by = Column('created_by', Integer(), ForeignKey('users.id'))
    finished_by = Column('finished_by', Integer(), ForeignKey('users.id'))
    created_at = Column('created_at', DateTime(), default=datetime.datetime.utcnow)
    finished_at = Column('finished_at', DateTime())

    org_r = relationship("Organisation")
    user_r = relationship("User")

    def __init__(
        self,
        org_id: int,
        title: str,
        description: str,
        status: str,
        assignee: int,
        created_by: int,
        finished_by: int,
        created_at: datetime,
        finished_at: datetime
    ):
        self.org_id = org_id
        self.created_by = created_by
        self.title = title
        self.description = description
        self.status = status
        self.assignee = assignee
        self.finished_by = finished_by
        self.created_at = created_at
        self.finished_at = finished_at

    def as_dict(self) -> dict:
        """
        :return: dict repr of a Task object
        """
        return {
            "org_id": self.org_id,
            "created_by": self.created_by,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "assignee": self.assignee,
            "finished_by": self.finished_by,
            "created_at": self.created_at,
            "finished_at": self.finished_at
        }
