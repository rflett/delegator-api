import datetime
from app import DBBase
from app.Models import Organisation, User, TaskPriority, TaskType, TaskStatus  # noqa
from sqlalchemy import Integer, String, DateTime, Column, ForeignKey
from sqlalchemy.orm import relationship


class Task(DBBase):
    __tablename__ = "tasks"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    type = Column('type', Integer(), ForeignKey('task_types.id'))
    description = Column('description', String())
    status = Column('status', String(), ForeignKey('task_statuses.status'))
    time_estimate = Column('time_estimate', Integer(), default=0)
    assignee = Column('assignee', Integer(), ForeignKey('users.id'))
    priority = Column('priority', Integer(), ForeignKey('task_priorities.priority'), default=1)
    created_by = Column('created_by', Integer(), ForeignKey('users.id'))
    created_at = Column('created_at', DateTime(), default=datetime.datetime.utcnow)
    finished_at = Column('finished_at', DateTime())

    orgs = relationship("Organisation")
    users = relationship("User")
    task_statuses = relationship("TaskStatus")
    task_types = relationship("TaskType")
    task_priorities = relationship("TaskPriority")

    def __init__(
        self,
        org_id: int,
        type: int,
        description: str,
        status: str,
        time_estimate: int,
        assignee: int,
        priority: int,
        created_by: int,
        created_at: datetime,
        finished_at: datetime
    ):
        self.org_id = org_id
        self.type = type
        self.description = description
        self.status = status
        self.time_estimate = time_estimate
        self.assignee = assignee
        self.priority = priority
        self.created_by = created_by
        self.created_at = created_at
        self.finished_at = finished_at

    def as_dict(self) -> dict:
        """
        :return: dict repr of a Task object
        """
        return {
            "org_id": self.org_id,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "time_estimate": self.time_estimate,
            "assignee": self.assignee,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "finished_at": self.finished_at
        }
