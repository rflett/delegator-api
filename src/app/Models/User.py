from app import DBBase
from sqlalchemy import Column, String


class User(DBBase):
    __tablename__ = "users"

    username = Column('username', String(32), primary_key=True)
    password = Column('password', String(32))
    auth_data = {'a': 'b'}

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def get_auth_data(self) -> dict:
        return {'username': self.username}
