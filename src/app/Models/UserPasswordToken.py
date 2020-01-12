import random
import string
import time

from app import db


class UserPasswordToken(db.Model):
    __tablename__ = "user_password_tokens"

    user_id = db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True)
    token = db.Column("token", db.String)
    created_at = db.Column("created_at", db.Integer)
    expire_after = db.Column("expire_after", db.Integer, default=86400)

    users = db.relationship("User", backref="password_token_user")

    def __init__(self, user_id: int, expire_after: int = 86400):
        self.user_id = user_id
        self.token = "".join([random.choice(string.ascii_letters + string.digits) for n in range(40)])
        self.created_at = int(time.time())
        self.expire_after = expire_after

    def as_dict(self) -> dict:
        """
        :return: dict repr of a UserPasswordToken object
        """
        return {
            "user_id": self.user_id,
            "token": self.token,
            "created_at": self.created_at,
            "expire_after": self.expire_after,
        }
