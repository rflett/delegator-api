from app import DBBase
from sqlalchemy import Column, Integer, String, DateTime


class TaskActivityLog(DBBase):
    __tablename__ = "user_auth_log"

    id = Column('id', Integer())
    org_id = Column('org_id', Integer())
    task_id = Column('task_id', Integer())
    action = Column('action', String())
    action_detail = Column('action_detail', String())
    created_at = Column('created_at', DateTime())

    def __init__(
        self,
        id: int,
        org_id: int,
        task_id: int,
        action: str,
        action_detail: str,
        created_at: int
    ):
        self.id = id
        self.org_id = org_id
        self.task_id = task_id
        self.action = action
        self.action_detail = action_detail
        self.created_at = created_at
