import binascii
import datetime
import hashlib
import uuid
from app import DBBase
from sqlalchemy import Column, String, Integer, DateTime


class Organisation(DBBase):
    __tablename__ = "organisations"

    id = Column('id', Integer(), primary_key=True)
    name = Column('name', String())
    jwt_aud = Column('jwt_aud', String())
    jwt_secret = Column('jwt_secret', String())
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(self, name: str):
        self.name = name
        self.jwt_aud = str(uuid.uuid4())
        self.jwt_secret = binascii.hexlify(
            hashlib.pbkdf2_hmac('sha256', uuid.uuid4().bytes, uuid.uuid4().bytes, 100000)).decode('ascii')

    def as_dict(self):
        """ Returns dict repr of BlacklistedToken """
        return {
            "name": self.name,
            "jwt_aud": self.jwt_aud,
            "jwt_secret": self.jwt_secret
        }
