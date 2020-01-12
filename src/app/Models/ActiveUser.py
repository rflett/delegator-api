import datetime

from app import db


class ActiveUser(db.Model):
    __tablename__ = "users_active"

    user_id = db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    first_name = db.Column("first_name", db.String)
    last_name = db.Column("last_name", db.String)
    last_active = db.Column("last_active", db.DateTime, default=datetime.datetime.utcnow)

    users = db.relationship("User")
    organisations = db.relationship("Organisation")

    def __init__(self, user_id: int, org_id: int, first_name: str, last_name: str, last_active: datetime):
        self.user_id = user_id
        self.org_id = org_id
        self.first_name = first_name
        self.last_name = last_name
        self.last_active = last_active

    def as_dict(self) -> dict:
        """
        :return: dict repr of a ActiveUser object
        """
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "last_active": str(self.last_active),
        }
