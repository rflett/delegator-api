from app import DBBase
from sqlalchemy import Column, Integer, String, DateTime


class UserActivityLog(DBBase):
    __tablename__ = "user_auth_log"

    org_id = Column('org_id', Integer())
    user_id = Column('user_id', Integer())
    action = Column('action', String())
    action_detail = Column('action_detail', String())

    def __init__(
        self,
        org_id: int,
        user_id: int,
        action: str,
        action_detail: str,
    ):
        self.id = id
        self.org_id = org_id
        self.user_id = user_id
        self.action = action
        self.action_detail = action_detail
