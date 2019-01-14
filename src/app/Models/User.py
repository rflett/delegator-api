import datetime
from app import DBBase
from app.Models.Enums import UserRole
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship


class User(DBBase):
    __tablename__ = "users"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    org = relationship("Organisation")
    username = Column('username', String())
    email = Column('email', String())
    first_name = Column('first_name', String())
    last_name = Column('last_name', String())
    password = Column('password', String())
    role = Column('role', String())
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            org_id: int,
            username: str,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            role: UserRole
    ):
        self.org_id = org_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = password
        self.role = role

    def as_dict(self) -> dict:
        """ Returns dict repr of User """
        return {
            "org_id": self.org_id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "password": self.password,
            "role": self.role
        }
