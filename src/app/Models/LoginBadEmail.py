import datetime
from app import DBBase
from sqlalchemy import Integer, String, DateTime, Column


class LoginBadEmail(DBBase):
    __tablename__ = "login_bad_emails"

    email = Column('email', String(), primary_key=True)
    failed_attempts = Column('failed_attempts', Integer(), default=1)
    failed_time = Column('failed_time', DateTime, default=datetime.datetime.utcnow)

    def __init__(self, email: str):
        self.email = email
