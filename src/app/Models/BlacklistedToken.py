from app import DBSession, DBBase
from sqlalchemy import Column, String

session = DBSession()


class BlacklistedToken(DBBase):
    __tablename__ = "blacklisted_tokens"

    id = Column('id', String(), primary_key=True)
    exp = Column('exp', String())

    def __init__(self, id: str, exp: int):
        self.id = id
        self.exp = exp
