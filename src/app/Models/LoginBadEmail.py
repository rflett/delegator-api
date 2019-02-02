import datetime
from app import DBBase, DBSession
from sqlalchemy import Integer, String, DateTime, Column


class LoginBadEmail(DBBase):
    __tablename__ = "login_bad_emails"

    email = Column('email', String(), primary_key=True)
    failed_attempts = Column('failed_attempts', Integer(), default=1)
    failed_time = Column('failed_time', DateTime, default=datetime.datetime.utcnow)

    def __init__(self, email: str):
        self.email = email

    def occured(self) -> None:
        self.failed_attempts += 1
        self.failed_time = datetime.datetime.utcnow()
        session = DBSession()
        session.add(self)
        session.commit()
