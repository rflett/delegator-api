import datetime
from app import db
from app.Models import Organisation, User, TaskPriority, TaskType, TaskStatus  # noqa
from sqlalchemy import Integer, String, DateTime, Column, ForeignKey
from sqlalchemy.orm import relationship


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column('id', db.Integer, primary_key=True)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    type = db.Column('type', db.Integer, db.ForeignKey('task_types.id'))
    description = db.Column('description', db.String)
    status = db.Column('status', db.String, db.ForeignKey('task_statuses.status'))
    time_estimate = db.Column('time_estimate', db.Integer, default=0)
    due_time = db.Column('due_time', db.DateTime)
    assignee = db.Column('assignee', db.Integer, db.ForeignKey('users.id'), default=None)
    priority = db.Column('priority', db.Integer, db.ForeignKey('task_priorities.priority'), default=1)
    created_by = db.Column('created_by', db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)
    finished_at = db.Column('finished_at', db.DateTime)

    orgs = db.relationship("Organisation")
    assignees = db.relationship("User", foreign_keys=[assignee])
    created_bys = db.relationship("User", foreign_keys=[created_by])
    task_statuses = db.relationship("TaskStatus")
    task_types = db.relationship("TaskType")
    task_priorities = db.relationship("TaskPriority")

    def __init__(
        self,
        org_id: int,
        type: int,
        description: str,
        status: str,
        time_estimate: int,
        due_time: datetime,
        assignee: int,
        priority: int,
        created_by: int,
        created_at: datetime,
        finished_at: datetime
    ):
        self.org_id = org_id
        self.type = type
        self.description = description
        self.status = status
        self.time_estimate = time_estimate
        self.due_time = due_time
        self.assignee = assignee
        self.priority = priority
        self.created_by = created_by
        self.created_at = created_at
        self.finished_at = finished_at

    def as_dict(self) -> dict:
        """
        :return: dict repr of a Task object
        """
        return {
            "id": self.id,
            "org_id": self.org_id,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "time_estimate": self.time_estimate,
            "due_time": self.due_time,
            "assignee": self.assignee,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "finished_at": self.finished_at
        }
