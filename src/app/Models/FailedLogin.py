import datetime
from app import DBBase
from sqlalchemy import Integer, String, DateTime, Column


class FailedLogin(DBBase):
    __tablename__ = "failed_login"

    email = Column('email', String(), primary_key=True)
    failed_attempts = Column('failed_attempts', Integer(), default=1)
    failed_time = Column('failed_time', DateTime, default=datetime.datetime.utcnow)

    def __init__(self, email: str):
        self.email = email
