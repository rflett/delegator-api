import datetime
from app import db


class DelayedTask(db.Model):
    __tablename__ = "tasks_delayed"

    id = db.Column('id', db.Integer, primary_key=True)
    task_id = db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'))
    delay_for = db.Column('delay_for', db.Integer)
    delayed_at = db.Column('delayed_at', db.DateTime, default=datetime.datetime.utcnow)
    snoozed = db.Column('snoozed', db.Boolean, default=False)
    expired = db.Column('expired', db.Boolean, default=False)

    tasks = db.relationship("Task")

    def __init__(
            self,
            task_id: int,
            delay_for: int,
            delayed_at: datetime,
            snoozed: bool = False,
            expired: bool = False
    ):
        self.task_id = task_id
        self.delay_for = delay_for
        self.delayed_at = delayed_at,
        self.snoozed = snoozed
        self.expired = expired

    def as_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "delay_for": self.delay_for,
            "delayed_at": self.delayed_at,
            "snoozed": self.snoozed,
            "expired": self.expired
        }
