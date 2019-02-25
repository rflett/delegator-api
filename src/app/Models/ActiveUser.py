import datetime
from app import DBBase
from app.Models import User, Organisation  # noqa
from sqlalchemy import Integer, String, Column, ForeignKey, DateTime
from sqlalchemy.orm import relationship


class ActiveUser(DBBase):
    __tablename__ = "users_active"

    user_id = Column('user_id', Integer(), ForeignKey('users.id'), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    first_name = Column('first_name', String())
    last_name = Column('last_name', String())
    last_active = Column('last_active', DateTime(), default=datetime.datetime.utcnow)

    users = relationship("User")
    organisations = relationship("Organisation")

    def __init__(
        self,
        user_id: int,
        org_id: int,
        first_name: str,
        last_name: str,
        last_active: datetime
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.first_name = first_name
        self.last_name = last_name
        self.last_active = last_active

    def as_dict(self) -> dict:
        """
        :return: dict repr of a ActiveUser object
        """
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "last_active": self.last_active
        }
