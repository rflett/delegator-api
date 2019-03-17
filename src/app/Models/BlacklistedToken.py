import datetime
from app import db
from sqlalchemy import Column, String, DateTime


class BlacklistedToken(db.Model):
    __tablename__ = "blacklisted_tokens"

    id = db.Column('id', db.String, primary_key=True)
    exp = db.Column('exp', db.String)
    created_at = db.Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(self, id: str, exp: int):
        self.id = id
        self.exp = exp

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a BlacklistedToken object
        """
        return {
            "id":  self.id,
            "exp": self.exp
        }
