import datetime
from app import db


class FailedLogin(db.Model):
    __tablename__ = "user_failed_logins"

    email = db.Column('email', db.String, primary_key=True)
    failed_attempts = db.Column('failed_attempts', db.Integer, default=1)
    failed_time = db.Column('failed_time', db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, email: str):
        self.email = email
