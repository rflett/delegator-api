import datetime
from app import DBSession, DBBase
from sqlalchemy import Column, String, DateTime

session = DBSession()


class BlacklistedToken(DBBase):
    __tablename__ = "blacklisted_tokens"

    id = Column('id', String(), primary_key=True)
    exp = Column('exp', String())
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(self, id: str, exp: int):
        self.id = id
        self.exp = exp
