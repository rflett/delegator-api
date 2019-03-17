import datetime
import typing
from app import db
from app.Models import Organisation   # noqa


class UserAuthLog(db.Model):
    __tablename__ = "user_auth_log"

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    org = db.relationship("Organisation")
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User")
    action = db.Column('action', db.String)
    action_detail = db.Column('action_detail', db.String, default=None)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    def __init__(
        self,
        org_id: int,
        user_id: int,
        action: str,
        action_detail: typing.Optional[str] = None
    ):
        self.org_id = org_id
        self.user_id = user_id
        self.action = action
        self.action_detail = action_detail
