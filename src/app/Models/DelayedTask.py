import datetime
import typing
from app import db


class DelayedTask(db.Model):
    __tablename__ = "tasks_delayed"

    task_id = db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'))
    delay_for = db.Column('delay_for', db.Integer)
    # https://docs.sqlalchemy.org/en/13/faq/ormconfiguration.html#how-do-i-map-a-table-that-has-no-primary-key
    delayed_at = db.Column('delayed_at', db.DateTime, default=datetime.datetime.utcnow, primary_key=True)
    delayed_by = db.Column('delayed_by', db.Integer, db.ForeignKey('users.id'))
    snoozed = db.Column('snoozed', db.DateTime, default=None)
    expired = db.Column('expired', db.DateTime, default=None)

    tasks = db.relationship("Task")
    users = db.relationship("User")

    def __init__(
            self,
            task_id: int,
            delay_for: int,
            delayed_at: datetime.datetime,
            delayed_by: int,
            snoozed: typing.Union[datetime.datetime, None] = None,
            expired: typing.Union[datetime.datetime, None] = None
    ):
        self.task_id = task_id
        self.delay_for = delay_for
        self.delayed_at = delayed_at
        self.delayed_by = delayed_by
        self.snoozed = snoozed
        self.expired = expired

    def as_dict(self):
        return {
            "task_id": self.task_id,
            "delay_for": self.delay_for,
            "delayed_at": self.delayed_at,
            "delayed_by": self.delayed_by,
            "snoozed": self.snoozed,
            "expired": self.expired
        }
