import datetime
import typing

from flask import current_app

from app.Extensions.Database import db


class DelayedTask(db.Model):
    __tablename__ = "tasks_delayed"

    task_id = db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"))
    delay_for = db.Column("delay_for", db.Integer)
    # https://docs.sqlalchemy.org/en/13/faq/ormconfiguration.html#how-do-i-map-a-table-that-has-no-primary-key
    delayed_at = db.Column("delayed_at", db.DateTime, default=datetime.datetime.utcnow, primary_key=True)
    delayed_by = db.Column("delayed_by", db.Integer, db.ForeignKey("users.id"))
    reason = db.Column("reason", db.Text, default=None)
    snoozed = db.Column("snoozed", db.DateTime, default=None)
    expired = db.Column("expired", db.DateTime, default=None)

    tasks = db.relationship("Task", backref="tasks")
    users = db.relationship("User", foreign_keys=[delayed_by], backref="users")

    def __init__(
        self,
        task_id: int,
        delay_for: int,
        delayed_at: datetime.datetime,
        delayed_by: int,
        reason: str = None,
        snoozed: typing.Union[datetime.datetime, None] = None,
        expired: typing.Union[datetime.datetime, None] = None,
    ):
        self.task_id = task_id
        self.delay_for = delay_for
        self.delayed_at = delayed_at
        self.delayed_by = delayed_by
        self.reason = reason
        self.snoozed = snoozed
        self.expired = expired

    def as_dict(self):
        if self.snoozed is None:
            snoozed = None
        else:
            snoozed = self.snoozed.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.expired is None:
            expired = None
        else:
            expired = self.expired.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        return {
            "task_id": self.task_id,
            "delay_for": self.delay_for,
            "delayed_at": self.delayed_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"]),
            "delayed_by": self.delayed_by,
            "reason": self.reason,
            "snoozed": snoozed,
            "expired": expired,
        }
