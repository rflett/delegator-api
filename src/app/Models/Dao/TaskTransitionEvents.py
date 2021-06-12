import datetime
import pytz
import uuid

from flask import current_app

from app.Extensions.Database import db


class TaskTransitionEvent(db.Model):
    __tablename__ = "task_transition_events"

    event_id = db.Column("id", db.String, primary_key=True)

    # TODO legacy will be removed when we transition to UUIDs
    task_id_legacy = db.Column("task_id_legacy", db.Integer, db.ForeignKey("tasks.id"))
    _task_id = db.Column("task_id", db.String, default=None)

    old_status = db.Column("old_status", db.String, db.ForeignKey("task_statuses.status"), default=None)
    new_status = db.Column("new_status", db.String, db.ForeignKey("task_statuses.status"))

    transitioned_at = db.Column("transitioned_at", db.DateTime, default=datetime.datetime.utcnow)
    transitioned_by = db.Column("transitioned_by", db.Integer, db.ForeignKey("users.id"))

    task = db.relationship("Task", foreign_keys=[task_id_legacy], backref="task")

    def __init__(self, task_id: int, transitioned_by: int, new_status: str, old_status: str = None):
        self.event_id = str(uuid.uuid4())
        self.task_id = task_id
        self.transitioned_by = transitioned_by
        self.new_status = new_status
        self.old_status = old_status

    @property
    def task_id(self):
        return self.task_id_legacy

    @task_id.setter
    def task_id(self, value: int):
        self.task_id_legacy = value

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskTransitionEvent object
        """
        transitioned_at = pytz.utc.localize(self.started_at)
        transitioned_at = transitioned_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "transitioned_at": transitioned_at,
            "transitioned_by": self.transitioned_by,
        }
