import datetime
from app import db


class DelayedTask(db.Model):
    __tablename__ = "tasks_delayed"

    task_id = db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
    delay_for = db.Column('delay_for', db.Integer)
    delayed_at = db.Column('delayed_at', db.DateTime, default=datetime.datetime.utcnow)

    tasks = db.relationship("Task")

    def __init__(self, task_id: int, delay_for: int, delayed_at: datetime = datetime.datetime.utcnow()):
        self.task_id = task_id
        self.delay_for = delay_for
        self.delayed_at = delayed_at

    def as_dict(self):
        return {
            "task_id": self.task_id,
            "delay_for": self.delay_for,
            "delayed_at": self.delayed_at
        }
