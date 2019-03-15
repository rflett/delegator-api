import datetime
import typing
from app import db
from app.Models import Organisation   # noqa
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship


class UserAuthLog(db.Model):
    __tablename__ = "user_auth_log"

    id = Column('id', Integer(), primary_key=True, autoincrement=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    org = relationship("Organisation")
    user_id = Column('user_id', Integer(), ForeignKey('users.id'))
    user = relationship("User")
    action = Column('action', String())
    action_detail = Column('action_detail', String(), default=None)
    created_at = Column('created_at', DateTime(), default=datetime.datetime.utcnow)

    def __init__(
        self,
        org_id: int,
        user_id: int,
        action: str,
        action_detail: typing.Optional[str] = None
    ):
        self.org_id = org_id
        self.user_id = user_id
        self.action = action
        self.action_detail = action_detail
