from app import DBBase
from sqlalchemy import Integer, String, DateTime, Column


class Task(DBBase):
    __tablename__ = "tasks"

    id = Column('id', Integer())
    org_id = Column('org_id', String())
    created_by = Column('created_by', Integer())
    title = Column('title', String())
    description = Column('description', String())
    status = Column('status', String())
    assignee = Column('assignee', Integer())
    finished_by = Column('finished_by', Integer())
    created_at = Column('created_at', DateTime())
    finished_at = Column('finished_at', DateTime())

    def __init__(
        self,
        id: int,
        org_id: int,
        created_by: int,
        title: str,
        description: str,
        status: str,
        assignee: int,
        finished_by: int,
        created_at: int,
        finished_at: int
    ):
        self.id = id
        self.org_id = org_id
        self.created_by = created_by
        self.title = title
        self.description = description
        self.status = status
        self.assignee = assignee
        self.finished_by = finished_by
        self.created_at = created_at
        self.finished_at = finished_at
