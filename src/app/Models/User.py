from app import DBBase
from sqlalchemy import Column, String, Integer, DateTime


class User(DBBase):
    __tablename__ = "users"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer())
    username = Column('username', String())
    email = Column('email', String())
    first_name = Column('first_name', String())
    last_name = Column('last_name', String())
    password = Column('password', String())
    role = Column('role', String())
    created_at = Column('created_at', DateTime())

    def __init__(
            self,
            org_id: int,
            username: str,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            role: str,
            created_at: int
    ):
        self.org_id = org_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = password
        self.role = role
        self.created_at = created_at
