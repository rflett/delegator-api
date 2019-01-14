import datetime
from app import DBBase
from app.Models import Organisation
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship


class UserAuthLog(DBBase):
    __tablename__ = "user_auth_log"

    id = Column('id', Integer(), primary_key=True, autoincrement=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    org = relationship("Organisation")
    user_id = Column('user_id', Integer(), ForeignKey('users.id'))
    user = relationship("User")
    action = Column('action', String())
    created_at = Column('created_at', DateTime(), default=datetime.datetime.utcnow)

    def __init__(
        self,
        org_id: int,
        user_id: int,
        action: str,
    ):
        self.org_id = org_id
        self.user_id = user_id
        self.action = action
