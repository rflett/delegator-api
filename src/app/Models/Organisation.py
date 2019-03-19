import binascii
import datetime
import hashlib
import uuid
from app import db


class Organisation(db.Model):
    __tablename__ = "organisations"

    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String)
    jwt_aud = db.Column('jwt_aud', db.String)
    jwt_secret = db.Column('jwt_secret', db.String)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, name: str):
        self.name = name
        self.jwt_aud = str(uuid.uuid4())
        self.jwt_secret = binascii.hexlify(
            hashlib.pbkdf2_hmac('sha256', uuid.uuid4().bytes, uuid.uuid4().bytes, 100000)).decode('ascii')

    def as_dict(self):
        """
        :return: The dict repr of an Organisation object
        """
        return {
            "name": self.name,
            "jwt_aud": self.jwt_aud,
            "jwt_secret": self.jwt_secret
        }
