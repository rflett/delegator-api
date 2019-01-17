from app import DBSession, DBBase
from sqlalchemy import Column, String

session = DBSession()


class BlacklistedToken(DBBase):
    __tablename__ = "blacklisted_tokens"

    id = Column('id', String(), primary_key=True)

    def __init__(self, id):
        self.id = id

